"""
Management command to import legacy edificaciones data from a CSV file.

Usage:
    python manage.py import_legacy_edificaciones --settings=config.settings.development
    python manage.py import_legacy_edificaciones --dry-run --settings=config.settings.development

Source file:
    backend/core_application/seeds/historico/EDIF_ALL.csv
    (119 columns, delimiter ';', BOM UTF-8)

Input columns (openpyxl 0-indexed after list(row)):
    row[2]  (col C)  RUC
    row[3]  (col D)  NOMBRE
    row[4]  (col E)  PROYECTO
    row[5]  (col F)  DPTOPRDI
    row[6]  (col G)  DIRECCION
    row[7]  (col H)  VALOROBRA
    row[8]  (col I)  PORCENTAJE
    row[9]  (col J)  SUBTOTAL
    row[11] (col L)  TOTAL
    row[12] (col M)  FECHA
    row[13] (col N)  DNI
    row[16] (col Q)  CODPAGO
    row[17] (col R)  NROEXPDTE
    row[18] (col S)  NROREV
    row[19] (col T)  ESPECIALIDAD

Output:
    Creates LiquidacionEdificaciones records via
    LiquidacionEdificacionesLegacyOrchestrator.crear_legacy_proceso().

Key changes from TSV version:
    - Read Excel with openpyxl (data_only=True)
    - Remove ESPECIALIDAD == 'TODAS' filter — process ALL rows
    - Pre-calculate via cotizar_legacy_proceso BEFORE insert, compare to Excel columns
    - Build descripcion_legacy with anomaly messages
    - numero_revision from NROREV (blank→1, anomaly>5 flagged)
    - denominacion_de_proyecto from PROYECTO column
    - EspecialidadRevision logged but NOT wired to DB (orchestrator auto-fills)

Documents with empty DNI are stored as tipo_documento=SIN_DOCUMENTO, numero_documento=00000000.
Documents with 8-char DNI are stored as tipo_documento=DNI.
All other documents are stored as tipo_documento=RUC.

Rows with errors are skipped (per-row try/except) and reported at the end.
"""

import csv
import logging
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from injector import Injector
from ninja.errors import HttpError


class VarianceError(Exception):
    """Variación excesiva entre el subtotal del Excel y el recalculado."""
    def __init__(self, message: str, subtotal_calculado=None, total_calculado=None):
        super().__init__(message)
        self.subtotal_calculado = subtotal_calculado
        self.total_calculado = total_calculado

from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import UbigeoDistrito
from modules.liquidaciones.di import LiquidacionesModule
from modules.liquidaciones.domain.constants import TipoDelegado, TipoLiquidacion
from modules.liquidaciones.domain.models.delegado import Delegado, DelegadoOperacion, LiquidacionDelegado
from modules.liquidaciones.domain.models.tipo_liquidacion import (
    TipoLiquidacion as TipoLiquidacionModel,
)
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_legacy.liquidacion_edificaciones_legacy_orchestrator import (
    LiquidacionEdificacionesLegacyOrchestrator,
)
from modules.liquidaciones.domain.resources import normalize_cip
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    EntidadInlineSchema,
    ProyectoCotizarSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_edificaciones_legacy_schemas import (
    CotizacionLegacyIn,
    LiquidacionEdificacionesLegacyIn,
    LiquidacionGeneralLegacyIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraDatosIn,
    LiquidacionPorcentajeObraIn,
    LiquidacionPorcentajeObraTarifaIn,
)
from modules.usuarios.di import UsuariosModule
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision, PerfilIngeniero
from modules.usuarios.domain.models.usuario import Usuario
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import (
    PerfilIngenieroCoreService,
)

logger = logging.getLogger(__name__)

# Default path to legacy data file
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "core_application" / "seeds" / "historico" / "EDIF_ALL.csv"

# CSV column indices — 0-indexed (list from csv.reader with delimiter ';')
# Header (row 1): ID=0 NRO=1 RUC=2 NOMBRE=3 PROYECTO=4 DPTOPRDI=5 DIRECCION=6
# VALOROBRA=7 PORCENTAJE=8 SUBTOTAL=9 IGV=10 TOTAL=11 FECHA=12 DNI=13
# RAZONSOCIAL=14 NROFACTURA=15 CODPAGO=16 NROEXPDTE=17 NROREV=18 ESPECIALIDAD=19
# NOTE: Many RH-slot and monetary indices changed vs old xlsx. See inline comments.
COL_ID = 0           # A (ID auto-incremental histórico)
COL_RUC = 2          # C
COL_NRO = 1          # B (número secuencial de la liquidación específica)
COL_NOMBRE = 3       # D
COL_PROYECTO = 4     # E
COL_DPTOPRDI = 5     # F
COL_DIRECCION = 6    # G
COL_VALOROBRA = 7    # H
COL_PORCENTAJE = 8   # I
COL_SUBTOTAL = 9     # J
COL_IGV = 10         # K
COL_TOTAL = 11       # L
COL_FECHA = 12       # M
COL_DNI = 13         # N
COL_RAZONSOCIAL = 14 # O
COL_CODPAGO = 16     # Q
COL_NROEXPDTE = 17   # R
COL_NROREV = 18      # S
COL_ESPECIALIDAD = 19  # T
COL_TFONO = 60         # was 60 in old xlsx (same index)
COL_TPERSONA = 61      # was 61 in old xlsx (same index)
COL_USUARIO = 32      # index 32 in EDIF_ALL.csv (was 32 in old xlsx — same)

# Max revisions constant (from liquidacion constants)
MAX_REVISIONES = 5

# ── RH / Delegado slot column indices (0-indexed, from list(row) iter_rows) ──────
# Header row: ID | NRO | RUC | NOMBRE | PROYECTO | DPTOPRDI | DIRECCION | VALOROBRA |
#             PORCENTAJE | SUBTOTAL | IGV | TOTAL | FECHA | DNI | RAZONSOCIAL |
#             NROFACTURA | CODPAGO | NROEXPDTE | NROREV | ESPECIALIDAD | ...
#             (continues with RH slot columns for slots 1-4)
#
# Slot fields per slot n (1..4):
#   DELEGADOn      – nombre del ingeniero CIP
#   CIPn           – número CIP
#   PERIODOn       – período (año) del RH
#   MESn           – mes del RH
#   FECHAPRESn     – fecha de presentación
#   FECHAREVIn     – fecha de revisión
#   NROORDENn      – número de orden
#   DICTAMENn      – dictamen (texto)
#   NRORHn         – número de RH
#   NROMMn          – número de memorandum
#
# Shared monetary fields (same value for every active slot in the row):
#   IMPBRUTO  | RENTACIP  | APORCODEMU | FONDOCOMUN | NETOHONORA
#
# Comprobante:
#   NROFACTURA – serie + número (e.g. "001-00001")

# Slot fields in the source CSV are grouped by field, not by slot.
# Updated for EDIF_ALL.csv header (119 columns, delimiter ';', BOM UTF-8)
COL_DELEGADO1 = 22
COL_DELEGADO2 = 23
COL_DELEGADO3 = 24
COL_DELEGADO4 = 25
COL_CIP1 = 79   # was 79 in old xlsx (same index)
COL_CIP2 = 80   # was 80
COL_CIP3 = 81   # was 81
COL_CIP4 = 82   # was 82
COL_PERIODO1 = 64  # was 62
COL_PERIODO2 = 65  # was 63
COL_PERIODO3 = 66  # was 64
COL_PERIODO4 = 67  # was 65
COL_MES1 = 68   # was 66
COL_MES2 = 69    # was 67
COL_MES3 = 70    # was 68
COL_MES4 = 71    # was 69
COL_FECHAPRES1 = 35  # was 36
COL_FECHAPRES2 = 38  # was 39
COL_FECHAPRES3 = 41  # was 42
COL_FECHAPRES4 = 44  # was 45
COL_FECHAREVI1 = 36  # was 37
COL_FECHAREVI2 = 39  # was 40
COL_FECHAREVI3 = 42  # was 43
COL_FECHAREVI4 = 45  # was 46
COL_NROORDEN1 = 37   # was 38
COL_NROORDEN2 = 40   # was 41
COL_NROORDEN3 = 43   # was 44
COL_NROORDEN4 = 46   # was 47
COL_DICTAMEN1 = 55
COL_DICTAMEN2 = 56
COL_DICTAMEN3 = 57
COL_DICTAMEN4 = 58
COL_NRORH1 = 87
COL_NRORH2 = 88
COL_NRORH3 = 89
COL_NRORH4 = 90
COL_NROMM1 = 91
COL_NROMM2 = 92
COL_NROMM3 = 93
COL_NROMM4 = 94

# Shared monetary fields (updated for EDIF_ALL.csv)
COL_IMPBRUTO = 26
COL_RENTACIP = 72   # was 72 (same index)
COL_APORCODEMU = 27
COL_FONDOCOMUN = 28
COL_NETOHONORA = 31
COL_SUBTOTAL = 9   # already defined above, listed here for completeness

# Comprobante
COL_NROFACTURA = 15
COL_TOTAL = 11

_RH_SLOT_COLUMNS = {
    1: (COL_DELEGADO1, COL_CIP1, COL_PERIODO1, COL_MES1, COL_FECHAPRES1, COL_FECHAREVI1, COL_NROORDEN1, COL_DICTAMEN1, COL_NRORH1, COL_NROMM1),
    2: (COL_DELEGADO2, COL_CIP2, COL_PERIODO2, COL_MES2, COL_FECHAPRES2, COL_FECHAREVI2, COL_NROORDEN2, COL_DICTAMEN2, COL_NRORH2, COL_NROMM2),
    3: (COL_DELEGADO3, COL_CIP3, COL_PERIODO3, COL_MES3, COL_FECHAPRES3, COL_FECHAREVI3, COL_NROORDEN3, COL_DICTAMEN3, COL_NRORH3, COL_NROMM3),
    4: (COL_DELEGADO4, COL_CIP4, COL_PERIODO4, COL_MES4, COL_FECHAPRES4, COL_FECHAREVI4, COL_NROORDEN4, COL_DICTAMEN4, COL_NRORH4, COL_NROMM4),
}

# ── Slot specialty mapping ────────────────────────────────────────────────────────
# Maps slot number (1..4) to the legacy XLSX display name (used for lookup
# before DB resolution, kept for readability in reports).
_SLOT_SPECIALTY_MAP = {
    1: "Estructuras / Civil",
    2: "Instalaciones Sanitarias",
    3: "Mecánico-Eléctricas",
    4: "Electrónica",
}

# ── Slot → EspecialidadRevision.nombre (canonical DB names) ────────────────────
# These are the actual EspecialidadRevision.nombre values in the DB.
_SLOT_SPECIALTY_DB_MAP = {
    1: "Ingeniería Civil",
    2: "Ingeniería Sanitaria",
    3: "Ingeniería Eléctrica y Mecánica Eléctrica",
    4: "Ingeniería Electrónica",
}

# Some legacy rows embed the CIP inside the delegado text rather than in the
# dedicated CIP column (e.g. "CIP 14720 Titular: ..."). This regex captures
# the numeric CIP at the start of the name so we can still process the slot.
_CIP_EMBEDDED_RE = re.compile(r'^\s*CIP\s+(\d{2,7})\b', re.IGNORECASE)


def _parse_fecha(raw) -> date:
    """Parse FECHA value (datetime object or string) -> date."""
    if not raw:
        raise ValueError("FECHA is empty")
    # openpyxl data_only=True returns datetime objects for date cells
    if isinstance(raw, datetime):
        return raw.date()
    raw_str = str(raw).strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw_str, fmt)
            return dt.date()
        except ValueError:
            pass
    raise ValueError(f"Cannot parse fecha: {raw_str!r}")


def _resolve_tipo_documento(dni: str) -> tuple[str, str]:
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


# Mapeo regex → (nombre canónico de distrito, nombre de provincia) en UbigeoDistrito.
# Los nombres históricos del Excel no siempre coinciden con la BD de ubigeo.
# provincia=None cuando el nombre del distrito ya es único.
_DISTRITO_SINONIMOS: list[tuple[str, tuple[str, str | None]]] = [
    (r"^CERCADO\s+DE\s+LIMA$", ("LIMA", None)),
    (r"^CENTRO\s+HIST[OÓ]RICO\s+DE\s+LIMA$", ("LIMA", None)),
    (r"^LIMA\s+CERCADO\s+Y\s+PROVINCIAL\s+LIMA$", ("LIMA", None)),
    (r"^ATE\s+VITARTE$", ("ATE", None)),
    (r"^LURIGANCHO\s*[-–]\s*CHOSICA$", ("LURIGANCHO", None)),
    (r"^BARRANCA\s*[-–]\s*NORTE$", ("BARRANCA", None)),
    # "SAN ANTONIO" es ambiguo (6 distritos homónimos). Acá es el de la provincia HUAROCHIRI.
    (r"^SAN\s+ANTONIO\s+DE\s+HUAROCHIRI$", ("SAN ANTONIO", "HUAROCHIRI")),
]


def _normalizar_distrito(nombre: str) -> tuple[str, str | None]:
    """Normaliza un nombre histórico de distrito a (nombre canónico, provincia o None)."""
    if not nombre:
        return "", None
    nombre = nombre.strip().upper()
    for pattern, (canon, provincia) in _DISTRITO_SINONIMOS:
        if re.match(pattern, nombre):
            return canon, provincia
    return nombre, None


def _build_orchestrator() -> LiquidacionEdificacionesLegacyOrchestrator:
    """
    Build a fully-injected LiquidacionEdificacionesLegacyOrchestrator.

    Creates a fresh Injector with the LiquidacionesModule and UsuariosModule
    bindings, then requests the orchestrator from the injector.
    """
    injector = Injector(
        [
            LiquidacionesModule(),
            UsuariosModule(),
        ]
    )
    return injector.get(LiquidacionEdificacionesLegacyOrchestrator)


# Mapeo ESPECIALIDAD (Excel) -> EspecialidadRevision.nombre
# NOTA: los valores deben coincidir EXACTAMENTE con los nombres canónicos de la BD local.
_ESPECIALIDAD_REVISION_MAP = {
    "Estructuras": "Ingeniería Civil",
    "Inst. Sanitarias": "Ingeniería Sanitaria",
    "Inst. Mecánico Eléctricas": "Ingeniería Eléctrica y Mecánica Eléctrica",
}


def _normalize_specialty(value: str) -> str:
    """Normaliza acentos/case para lookup robusto de ESPECIALIDAD."""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return normalized.lower().strip()


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


def _resolve_especialidad_revision(especialidad_str: str):
    """
    Map ESPECIALIDAD (Excel) -> EspecialidadRevision or None.

    Normaliza acentos/case tanto el valor del Excel como el nombre en BD
    (lookup en memoria), para resistir tildes y variantes de escritura.
    """
    if not especialidad_str:
        return None
    target = _normalize_specialty(especialidad_str)
    for excel_value, revision_nombre in _ESPECIALIDAD_REVISION_MAP.items():
        if _normalize_specialty(excel_value) == target:
            revision_norm = _normalize_specialty(revision_nombre)
            for esp in EspecialidadRevision.objects.all():
                if _normalize_specialty(esp.nombre) == revision_norm:
                    return esp
            return None
    return None


def _get_or_create_system_user() -> Usuario:
    """
    Return the first active superuser, creating a 'system' user if none exist.

    The system user is used for legacy imports where no authenticated user is present.
    """
    superuser = Usuario.objects.filter(is_superuser=True, is_active=True).first()
    if superuser:
        return superuser

    system_user, created = Usuario.objects.get_or_create(
        username="system",
        defaults={
            "is_superuser": True,
            "is_staff": True,
            "is_active": True,
            "dni": "00000000",
        },
    )
    if created:
        logger.info("Created system user (id=%s)", system_user.id)
    return system_user


def _normalize_usuario_to_username(usuario_raw) -> str | None:
    """
    Transform a USUARIO raw value into a normalized username slug.

    Rules:
        - Strip accents (e.g., 'Ñ' -> 'n', 'Ó' -> 'o')
        - Convert to lowercase
        - Replace whitespace with dots
        - Keep only alphanumeric, dots, underscores, hyphens
        - Return None if input is empty/blank/NULL

    Example:
        'SANDRA OJEDA'       -> 'sandra.ojeda'
        'MARIBEL QUIÑONES'   -> 'maribel.quinones'
    """
    if usuario_raw is None:
        return None
    text = str(usuario_raw).strip()
    if not text or text.upper() == "NULL":
        return None

    # Normalize: strip accents using NFKD decomposition
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))

    # Lowercase
    normalized = normalized.lower()

    # Replace whitespace with dot
    normalized = re.sub(r"\s+", ".", normalized)

    # Keep only valid username characters (alphanumeric, dots, underscores, hyphens)
    normalized = re.sub(r"[^a-z0-9._-]", "", normalized)

    # Remove leading/trailing dots, underscores, hyphens
    normalized = normalized.strip(".-_")

    if not normalized:
        return None

    return normalized


def _get_or_create_usuario_from_usuario(usuario_raw) -> Usuario:
    """
    Get or create a Usuario from a USUARIO raw value.

    If USUARIO is blank/empty, returns the system user (fallback).

    For new users:
        - username = normalized USUARIO
        - password = 'admin'
        - dni = None (no DNI for these legacy users)
        - is_active = True

    For existing users:
        - Does NOT overwrite the password.
    """
    username = _normalize_usuario_to_username(usuario_raw)
    if not username:
        return _get_or_create_system_user()

    # Try to find existing user by username
    existing = Usuario.objects.filter(username=username).first()
    if existing:
        return existing

    # Create new user with normalized username
    # email unique=True -> usar un email determinista por username para no chocar UNIQUE.
    user = Usuario.objects.create(
        username=username,
        email=f"{username}@legacy.local",
        dni=None,
    )
    user.set_password("admin")
    user.save(using=Usuario.objects.db)
    logger.info("Created legacy user '%s' from USUARIO='%s'", username, usuario_raw)
    return user


# ── RH Slot Parsing Helpers ───────────────────────────────────────────────────────


def _parse_comprobante(row: list) -> dict:
    """
    Parse NROFACTURA into serie and numero.

    The legacy NROFACTURA format is typically '001-00001' (serie-numero).
    Split on the first '-' found; strip whitespace.

    Returns:
        {"serie": str, "numero": str} if parseable.
        {"serie": None, "numero": None, "raw": str} if empty/invalid.
    """
    raw = row[COL_NROFACTURA] if len(row) > COL_NROFACTURA else None
    if raw is None:
        return {"serie": None, "numero": None, "raw": None}
    text = str(raw).strip()
    if not text or text.upper() in ("NULL", ""):
        return {"serie": None, "numero": None, "raw": text}

    # Split on first '-'
    if "-" in text:
        parts = text.split("-", 1)
        serie = parts[0].strip()
        numero = parts[1].strip()
        return {"serie": serie, "numero": numero, "raw": text}

    # No separator — treat entire as numero, serie empty
    return {"serie": None, "numero": text, "raw": text}


def _coerce_int(raw) -> int | None:
    """Coerce a raw cell value to int. Returns None if empty/invalid."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() == "NULL":
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def _coerce_month(raw) -> int | None:
    """
    Coerce MES cell value to int in range 1..12.

    Returns None if absent, null, or out of range.
    Never infers from FECHA.
    """
    val = _coerce_int(raw)
    if val is None:
        return None
    if 1 <= val <= 12:
        return val
    return None  # invalid month — skip slot


def _parse_rh_slot(
    row: list,
    slot_num: int,
) -> dict | None:
    """
    Parse a single RH slot (1..4) from a row.

    Returns None if the slot has no assigned delegate/CIP (skip signal).

    Otherwise returns a dict with all slot fields:
        {
            "slot": int,
            "specialty": str,
            "delegado": str or None,       # raw nombre
            "cip": int or None,
            "periodo": int or None,         # PERIODO
            "mes": int or None,             # 1..12 or None if invalid/absent
            "fecha_presentacion": date or None,
            "fecha_revision": date or None,
            "nro_orden": int or None,
            "dictamen": str or None,
            "nro_rh": int or None,
            "nro_mm": int or None,
            "skip_reason": None,
        }

    Skip reasons (returns None):
        - No CIP value present
        - No DELEGADO value present

    Monetary fields are NOT included — those are shared per row and parsed
    separately via _parse_row_monetary().
    """
    try:
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
        ) = _RH_SLOT_COLUMNS[slot_num]
    except KeyError:
        return None

    def _col(idx: int):
        return row[idx] if len(row) > idx else None

    cip_raw = _col(col_cip)
    cip = _coerce_int(cip_raw)

    delegado_raw = _col(col_delegado)
    delegado_text = (
        str(delegado_raw).strip()
        if delegado_raw is not None
        else None
    )
    if not delegado_text or delegado_text.upper() == "NULL":
        # No delegate — skip slot
        return None

    # Fallback: some legacy rows embed the CIP inside the delegado text rather
    # than in the dedicated CIP column (e.g. "CIP 14720 Titular: ..."). If the
    # CIP column is missing, extract it from the name to avoid skipping slots
    # that actually carry delegate data.
    if cip is None:
        embedded = _coerce_int(_CIP_EMBEDDED_RE.search(delegado_text).group(1)) if _CIP_EMBEDDED_RE.search(delegado_text) else None
        if embedded is not None:
            cip = embedded

    if cip is None:
        # No CIP — skip slot
        return None

    periodo = _coerce_int(_col(col_periodo))
    mes = _coerce_month(_col(col_mes))

    # Parse dates — return None if invalid/absent; never raise
    def _parse_date(raw):
        if raw is None:
            return None
        if isinstance(raw, datetime):
            return raw.date()
        text = str(raw).strip()
        if not text or text.upper() == "NULL":
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        return None  # invalid — include None in result, don't skip slot

    return {
        "slot": slot_num,
        "specialty": _SLOT_SPECIALTY_MAP[slot_num],
        "delegado": delegado_text,
        "cip": cip,
        "periodo": periodo,
        "mes": mes,
        "fecha_presentacion": _parse_date(_col(col_fecha_pres)),
        "fecha_revision": _parse_date(_col(col_fecha_rev)),
        "nro_orden": _coerce_int(_col(col_nro_orden)),
        "dictamen": str(_col(col_dictamen)).strip() if _col(col_dictamen) is not None else None,
        "nro_rh": _coerce_int(_col(col_nro_rh)),
        "nro_mm": _coerce_int(_col(col_nro_mm)),
        "skip_reason": None,
    }


def _parse_row_monetary(row: list) -> dict:
    """
    Parse shared monetary fields from a row.

    These are fixed source values shared by all active slots in the same row:
        IMPBRUTO, RENTACIP, APORCODEMU, FONDOCOMUN, NETOHONORA, SUBTOTAL.

    Returns dict with Decimal values (or None if absent/invalid):
        {
            "imp_bruto": Decimal | None,
            "renta_cip": Decimal | None,
            "aporte_codemu": Decimal | None,
            "fondo_comun": Decimal | None,
            "neto_honorario": Decimal | None,
            "subtotal": Decimal | None,
        }
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
        "imp_bruto": _dec(row[COL_IMPBRUTO] if len(row) > COL_IMPBRUTO else None),
        "renta_cip": _dec(row[COL_RENTACIP] if len(row) > COL_RENTACIP else None),
        "aporte_codemu": _dec(row[COL_APORCODEMU] if len(row) > COL_APORCODEMU else None),
        "fondo_comun": _dec(row[COL_FONDOCOMUN] if len(row) > COL_FONDOCOMUN else None),
        "neto_honorario": _dec(row[COL_NETOHONORA] if len(row) > COL_NETOHONORA else None),
        "subtotal": _dec(row[COL_SUBTOTAL] if len(row) > COL_SUBTOTAL else None),
    }


# ── Phase 2: RH Delegado helpers (no DB writes in Phase 2; counters only) ────────

def _resolve_slot_especialidad_revision(slot_num: int) -> EspecialidadRevision | None:
    """
    Resolve EspecialidadRevision for a slot number (1..4) using the canonical
    DB names from _SLOT_SPECIALTY_DB_MAP.

    Returns the EspecialidadRevision object or None if not found.
    """
    db_nombre = _SLOT_SPECIALTY_DB_MAP.get(slot_num)
    if not db_nombre:
        return None
    return EspecialidadRevision.objects.filter(nombre=db_nombre).first()


def _ensure_perfil_ingeniero_by_cip(cip: int, dry_run: bool = False) -> tuple[PerfilIngeniero | None, str]:
    """
    Get or create a PerfilIngeniero by normalized CIP, hydrating from CIP endpoint.

    Reuses existing local profile if found. Otherwise calls the CIP endpoint via
    PerfilIngenieroCoreService.hydrate_perfil_from_cip and creates a full profile
    from the response.

    Does NOT create blank/minimal profiles — if the CIP endpoint returns no data
    or is unavailable, returns SIN_COLEGIADO or ERROR_CIP and skips profile creation.

    Args:
        cip: Integer CIP number.
        dry_run: If True, do not write to DB; report what would happen.

    Returns:
        (perfil_ingeniero, status) where status is one of:
            "YA_EXISTE"            - found existing local profile, reused as-is
            "CREADO_DESDE_CIP"    - created new profile from CIP endpoint data
            "ACTUALIZADO_DESDE_CIP" - updated existing profile from CIP endpoint data
            "SIN_COLEGIADO"       - CIP endpoint returned no data (404 or null)
            "ERROR_CIP"           - CIP service unavailable after retries
            "ERROR"               - unexpected failure (invalid CIP, DB error, etc.)
    """
    service = PerfilIngenieroCoreService()
    return service.hydrate_perfil_from_cip(str(cip), dry_run=dry_run)


def _ensure_delegado_for_perfil(
    perfil: PerfilIngeniero,
    dry_run: bool = False,
) -> tuple[Delegado | None, str]:
    """
    Get or create a Delegado for a PerfilIngeniero.

    Args:
        perfil: PerfilIngeniero instance.
        dry_run: If True, do not write to DB.

    Returns:
        (delegado, status) where status is "CREADO", "YA_EXISTE", or "ERROR".
    """
    if dry_run:
        existing = Delegado.objects.filter(perfil_ingeniero=perfil).first()
        if existing:
            return existing, "YA_EXISTE"
        return None, "CREADO"

    try:
        delegado, created = Delegado.objects.get_or_create(perfil_ingeniero=perfil)
    except IntegrityError:
        return None, "ERROR"
    return delegado, "CREADO" if created else "YA_EXISTE"


def _ensure_delegado_operacion(
    delegado: Delegado,
    municipalidad: type[Municipalidad],  # noqa: F821
    tipo_liquidacion: type[TipoLiquidacion],  # noqa: F821
    especialidad_revision: EspecialidadRevision,
    dry_run: bool = False,
) -> tuple[DelegadoOperacion | None, str]:
    """
    Get or create a DelegadoOperacion for a delegate/municipalidad/tipo_liquidacion/specialty.

    The DelegadoOperacion unique constraint is:
        (delegado, municipalidad, tipo_liquidacion)
    — it does NOT include especialidad_revision.

    Conflict handling:
        - If an existing DelegadoOperacion has the same (delegado, municipalidad,
          tipo_liquidacion) but a DIFFERENT especialidad_revision, we CANNOT
          create a duplicate. We report "CONFLICTO" and reuse the existing one.
        - If tipo_liquidacion is None (legacy NULL), we look for existing with
          NULL tipo_liquidacion first (backward compatibility with seed_delegados).
        - If the existing record has the SAME especialidad_revision, we reuse it
          ("YA_EXISTE").

    Args:
        delegado: Delegado instance.
        municipalidad: Financiera.Municipalidad instance.
        tipo_liquidacion: TipoLiquidacion instance (may be None for legacy NULL).
        especialidad_revision: EspecialidadRevision instance.
        dry_run: If True, do not write to DB.

    Returns:
        (delegado_operacion, status) where status is:
            "CREADO"     - created new
            "YA_EXISTE"  - reused existing with same specialty
            "CONFLICTO"  - existing with different specialty; will reuse but report conflict
            "ERROR"      - unexpected failure
    """
    if dry_run:
        # Check in dry-run mode without writing
        existing = _get_existing_delegado_operacion(
            delegado, municipalidad, tipo_liquidacion
        )
        if existing is None:
            return None, "CREADO"
        if existing.especialidad_revision_id == especialidad_revision.id:
            return existing, "YA_EXISTE"
        return existing, "CONFLICTO"

    # Non-dry-run path
    try:
        # First try the exact lookup (delegado, municipalidad, tipo_liquidacion, especialidad)
        existing = DelegadoOperacion.objects.filter(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            especialidad_revision=especialidad_revision,
        ).first()
        if existing:
            return existing, "YA_EXISTE"

        # Check for existing with same (delegado, municipalidad, tipo_liquidacion)
        # but different specialty — this is a conflict we cannot resolve blindly
        conflict = _get_existing_delegado_operacion(delegado, municipalidad, tipo_liquidacion)
        if conflict is not None and conflict.especialidad_revision_id != especialidad_revision.id:
            # Report conflict but still return the existing one for continuation
            return conflict, "CONFLICTO"

        # No conflict — create new
        operation = DelegadoOperacion.objects.create(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            especialidad_revision=especialidad_revision,
            tipo=TipoDelegado.TITULAR,
        )
        return operation, "CREADO"
    except Exception:  # noqa: BLE001
        return None, "ERROR"


def _get_existing_delegado_operacion(
    delegado: Delegado,
    municipalidad: type[Municipalidad],  # noqa: F821
    tipo_liquidacion: type[TipoLiquidacion] | None,  # noqa: F821
) -> DelegadoOperacion | None:
    """
    Find an existing DelegadoOperacion matching (delegado, municipalidad, tipo_liquidacion).
    Used internally by _ensure_delegado_operacion for conflict detection.
    """
    qs = DelegadoOperacion.objects.filter(
        delegado=delegado,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_liquidacion,
    )
    return qs.first()


# ── Phase 4: LiquidacionComprobante helpers ──────────────────────────────────────


def _parse_total(row: list) -> Decimal | None:
    """
    Parse TOTAL column from a legacy row into a Decimal.

    Returns None if absent/invalid/zero.
    """
    if len(row) <= COL_TOTAL:
        return None
    raw = row[COL_TOTAL]
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


def _tipo_comprobante_from_nrofactura(raw: str | None) -> str | None:
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


def _upsert_liquidacion_comprobante(
    liquidacion: LiquidacionGeneral,
    comprobante_data: dict,
    total: Decimal | None,
    dry_run: bool = False,
) -> tuple[LiquidacionComprobante | None, str]:
    """
    Create or update a LiquidacionComprobante for a LiquidacionGeneral.

    Idempotency: finds existing active comprobante (activo=True) for this
    liquidation and updates it in-place rather than creating a duplicate.

    The UniqueConstraint on (liquidacion_general, activo=True) means at most
    one active comprobante can exist per liquidation — the model enforces this.

    Args:
        liquidacion: LiquidacionGeneral instance (same-row).
        comprobante_data: dict from _parse_comprobante with keys:
            serie, numero, raw (NROFACTURA original)
        total: Decimal total from legacy TOTAL column (stored as monto).
        dry_run: If True, do not write to DB.

    Returns:
        (comprobante, status) where status is:
            "CREADO"     - created new active comprobante
            "ACTUALIZADO" - updated existing active comprobante
            "OMITIDO"     - NROFACTURA blank/malformed; no comprobante created or updated
            "ERROR"       - unexpected failure
    """
    raw_nrofactura = comprobante_data.get("raw")
    serie = comprobante_data.get("serie")
    numero = comprobante_data.get("numero")

    # Skip if NROFACTURA is blank or malformed (neither serie nor numero)
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

        tipo = _tipo_comprobante_from_nrofactura(raw_nrofactura)

        if existing:
            # Update existing active comprobante in-place
            existing.serie = serie
            existing.numero = numero
            existing.tipo_comprobante = tipo
            existing.monto = total
            existing.save()
            return existing, "ACTUALIZADO"

        # Create new comprobante
        comp = LiquidacionComprobante.objects.create(
            liquidacion_general=liquidacion,
            tipo_comprobante=tipo,
            serie=serie,
            numero=numero,
            monto=total,
            activo=True,
        )
        return comp, "CREADO"
    except Exception:  # noqa: BLE001
        return None, "ERROR"


# ── Phase 3: LiquidacionDelegado + DetalleHonorarioDelegado helpers ───────────────


def _find_same_row_liquidacion(
    expediente: str | None,
    numero_revision: int,
    municipalidad: type[Municipalidad],  # noqa: F821
) -> tuple[LiquidacionGeneral | None, str]:
    """
    Find the LiquidacionGeneral created from the same legacy row.

    Uses (expediente, numero_revision, municipalidad, legacy=True) to recover
    the row-created liquidation.

    Returns:
        (liquidacion, status) where status is:
            "ENCONTRADO"   - exactly one matching record
            "NO_ENCONTRADO" - no matching record
            "AMBIGUO"       - more than one matching record
    """
    if expediente is None:
        return None, "NO_ENCONTRADO"

    qs = LiquidacionGeneral.objects.filter(
        expediente=expediente,
        numero_revision=numero_revision,
        municipalidad=municipalidad,
        legacy=True,
    )
    count = qs.count()
    if count == 1:
        return qs.first(), "ENCONTRADO"
    elif count == 0:
        return None, "NO_ENCONTRADO"
    else:
        # Multiple matches — ambiguous, skip
        return None, "AMBIGUO"


def _ensure_liquidacion_delegado(
    liquidacion: LiquidacionGeneral,
    delegado: Delegado,
    especialidad_revision: EspecialidadRevision,
    delegado_operacion: DelegadoOperacion | None,
    slot_data: dict,
    dry_run: bool = False,
) -> tuple[LiquidacionDelegado | None, str]:
    """
    Get or create a LiquidacionDelegado for the given liquidation/delegado/specialty.

    Idempotency key: (liquidacion, delegado, especialidad_revision).
    If exists, returns (existing, "YA_EXISTE").
    If created, returns (new, "CREADO").

    Args:
        liquidacion: LiquidacionGeneral instance (same-row).
        delegado: Delegado instance.
        especialidad_revision: EspecialidadRevision instance.
        delegado_operacion: DelegadoOperacion instance or None.
        slot_data: parsed RH slot dict with keys:
            - periodo, mes, fecha_presentacion, fecha_revision
            - numero_rh (from nro_rh or nro_mm slot field)
            - dictamen (from dictamen slot field)
        dry_run: If True, do not write to DB.

    Returns:
        (liquidacion_delegado, status) where status is "CREADO", "YA_EXISTE", or "ERROR".
    """
    if dry_run:
        existing = LiquidacionDelegado.objects.filter(
            liquidacion=liquidacion,
            delegado=delegado,
            especialidad_revision=especialidad_revision,
        ).first()
        return (existing, "YA_EXISTE" if existing else "CREADO")

    try:
        existing = LiquidacionDelegado.objects.filter(
            liquidacion=liquidacion,
            delegado=delegado,
            especialidad_revision=especialidad_revision,
        ).first()
        if existing:
            return existing, "YA_EXISTE"

        ld = LiquidacionDelegado.objects.create(
            liquidacion=liquidacion,
            delegado=delegado,
            especialidad_revision=especialidad_revision,
            delegado_operacion=delegado_operacion,
            periodo=slot_data.get("periodo"),
            mes=slot_data.get("mes"),
            fecha_presentacion=slot_data.get("fecha_presentacion"),
            fecha_revision=slot_data.get("fecha_revision"),
            numero_rh=str(slot_data.get("nro_rh")) if slot_data.get("nro_rh") is not None else None,
            dictamen_revision=slot_data.get("dictamen"),
        )
        return ld, "CREADO"
    except Exception:  # noqa: BLE001
        return None, "ERROR"


def _ensure_detalle_honorario_delegado(
    liquidacion_delegado: LiquidacionDelegado,
    monetary: dict,
    dry_run: bool = False,
) -> tuple[DetalleHonorarioDelegado | None, str]:
    """
    Get or create a DetalleHonorarioDelegado for a LiquidacionDelegado.

    Idempotency key: (liquidacion_delegado, recibo_mensual is null).
    Since legacy imports have no monthly recibo, we always use recibo_mensual=None.

    Args:
        liquidacion_delegado: LiquidacionDelegado instance.
        monetary: dict with legacy monetary fields:
            - imp_bruto, renta_cip, aporte_codemu, fondo_comun, neto_honorario
            - subtotal (from the fixed legacy RH source per current parser)
        dry_run: If True, do not write to DB.

    Returns:
        (detalle, status) where status is "CREADO", "YA_EXISTE", or "ERROR".
    """
    if dry_run:
        existing = DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado=liquidacion_delegado,
            recibo_mensual__isnull=True,
        ).first()
        return (existing, "YA_EXISTE" if existing else "CREADO")

    try:
        existing = DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado=liquidacion_delegado,
            recibo_mensual__isnull=True,
        ).first()
        if existing:
            return existing, "YA_EXISTE"

        detalle = DetalleHonorarioDelegado.objects.create(
            recibo_mensual=None,
            liquidacion_delegado=liquidacion_delegado,
            imp_bruto=monetary.get("imp_bruto") or Decimal("0"),
            sub_total=monetary.get("subtotal"),
            renta_cip=monetary.get("renta_cip"),
            aporte_codemu=monetary.get("aporte_codemu"),
            fondo_comun=monetary.get("fondo_comun"),
            neto_honorario=monetary.get("neto_honorario"),
            tasa_delegado=None,
        )
        return detalle, "CREADO"
    except Exception:  # noqa: BLE001
        return None, "ERROR"


class Command(BaseCommand):
    help = "Import legacy edificaciones data from CSV file via LiquidacionEdificacionesLegacyOrchestrator"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Read and validate rows without writing to the database",
        )
        parser.add_argument(
            "--rechazar-dif-alta",
            action="store_true",
            help="Rechazar filas donde la diferencia entre el subtotal recalculado y el "
                 "legacy supere el umbral (default 1). Desactivado por defecto.",
        )
        parser.add_argument(
            "--umbral-dif",
            type=float,
            default=1.0,
            help="Umbral de diferencia (S/.) para --rechazar-dif-alta (default 1.0). "
                 "Solo suben filas con diferencia <= umbral.",
        )
        parser.add_argument(
            "--data-path",
            type=str,
            default=None,
            help=f"Ruta al archivo CSV (default: {DEFAULT_DATA_PATH})",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Log a checkpoint every N rows (default: 100)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Procesar solo las primeras N filas de datos del archivo legacy",
        )
        parser.add_argument(
            "--fecha-desde",
            type=str,
            default=None,
            help="Procesar solo filas con FECHA mayor o igual a esta fecha (dd/mm/yyyy o yyyy-mm-dd)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Eliminar TODAS las LiquidacionGeneral existentes (y registros de finanzas "
                 "que bloquean su borrado) antes de importar",
        )
        parser.add_argument(
            "--solo-reporte",
            action="store_true",
            help="Solo generar reporte_legacy_detallado.csv/.xlsx sin importar ni tocar la BD",
        )
        parser.add_argument(
            "--dry-run-rh",
            action="store_true",
            help="Phase 1: parse RH delegado slots and produce a summary report. "
                 "No DB writes for RH entities. Implies --dry-run for RH path.",
        )

    def _reset_liquidaciones(self) -> None:
        """
        Elimina TODAS las LiquidacionGeneral y los registros de finanzas que las
        referencian (recibos de honorario, detalles, registros de pago), en orden
        correcto para no violar las FKs con on_delete=PROTECT.
        """
        from modules.finanzas.domain.models.detalle_honorario_delegado import (
            DetalleHonorarioDelegado,
        )
        from modules.finanzas.domain.models.detalle_honorario_inspector import (
            DetalleHonorarioInspector,
        )
        from modules.finanzas.domain.models.recibo_honorario import (
            ReciboHonorarioDelegado,
        )
        from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
            ReciboHonorarioDelegadoMensual,
        )
        from modules.finanzas.domain.models.recibo_honorario_inspector import (
            ReciboHonorarioInspector,
        )
        from modules.finanzas.domain.models.recibo_honorario_inspector_mensual import (
            ReciboHonorarioInspectorMensual,
        )
        from modules.finanzas.domain.models.registro_pago_inspector import (
            RegistroPagoInspector,
        )
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
            LiquidacionGeneral,
        )

        if self.dry_run:
            self._log(self.style.WARNING(
                f"  [DRY-RUN] Se eliminarían {LiquidacionGeneral.objects.count()} LiquidacionGeneral "
                f"(y RH de finanzas asociados)"
            ))
            return

        # Order matters: child details first, then headers, then pagos, then liquidaciones.
        DetalleHonorarioDelegado.objects.all().delete()
        DetalleHonorarioInspector.objects.all().delete()
        ReciboHonorarioDelegadoMensual.objects.all().delete()
        ReciboHonorarioInspectorMensual.objects.all().delete()
        ReciboHonorarioDelegado.objects.all().delete()
        ReciboHonorarioInspector.objects.all().delete()
        RegistroPagoInspector.objects.all().delete()
        deleted, _ = LiquidacionGeneral.objects.all().delete()
        self._log(f"  Eliminadas {deleted} filas (LiquidacionGeneral y relacionados).")

    def handle(self, *args, **options):
        self.dry_run_rh = bool(options.get("dry_run_rh", False))
        self.dry_run = bool(options["dry_run"]) or self.dry_run_rh
        self.batch_size = int(options["batch_size"])
        self.reset = bool(options.get("reset", False))
        self.solo_reporte = bool(options.get("solo_report", False)) or bool(options.get("solo_reporte", False))
        self.rechazar_dif_alta = bool(options.get("rechazar_dif_alta", False))
        self.umbral_dif = Decimal(str(options.get("umbral_dif", 1.0)))
        fecha_desde_raw = options.get("fecha_desde")
        self.fecha_desde = None
        if fecha_desde_raw:
            try:
                self.fecha_desde = _parse_fecha(fecha_desde_raw)
            except ValueError as exc:
                raise CommandError(f"--fecha-desde inválida: {fecha_desde_raw!r}") from exc

        data_path = Path(options["data_path"]) if options["data_path"] else DEFAULT_DATA_PATH
        if not data_path.exists():
            raise CommandError(f"Data file not found: {data_path}")

        self._log("\n[import_legacy_edificaciones] Starting...")
        self._log(f"  Source: {data_path}")
        if self.fecha_desde is not None:
            self._log(self.style.WARNING(f"  --fecha-desde: procesando FECHA >= {self.fecha_desde}"))
        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE — no database writes"))

        # Build injector and resolve orchestrator
        self._log("  Resolving orchestrator...")
        orchestrator = _build_orchestrator()
        self._log("  Orchestrator ready.")

        # Read CSV
        rows = self._read_csv(data_path)
        limit = options.get("limit")
        if limit is not None:
            if limit < 1:
                raise CommandError("--limit debe ser mayor o igual a 1")
            rows = rows[:limit]
            self._log(self.style.WARNING(f"  --limit: procesando solo las primeras {limit} filas"))
        total_rows = len(rows)
        self._log(f"  Total rows to process: {total_rows}")

        # ── Solo reporte: no toca la BD ─────────────────────────────────────
        if self.solo_reporte:
            self._log(self.style.WARNING("  --solo-reporte: NO se importa, solo se genera el detallado."))
            self._generar_reporte_detallado(rows, orchestrator, data_path.parent)
            return

        # Resolve system user (first superuser or create 'system') for fallback
        system_user = _get_or_create_system_user()
        self._log(f"  System user fallback: username={system_user.username}")

        # Optional reset: wipe all existing liquidaciones before importing
        if self.reset:
            self._log(self.style.WARNING("  --reset: eliminando LiquidacionGeneral existentes..."))
            self._reset_liquidaciones()
            self._log(self.style.SUCCESS("  Reset completado."))

        # Each run writes to its own folder so migration reports are auditable.
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = Path(__file__).resolve().parents[5] / "result" / "EDIF" / run_id
        result_dir.mkdir(parents=True, exist_ok=True)
        report_csv_path = result_dir / "reporte_ingesta_legacy.csv"
        report_file = report_csv_path.open("w", newline="", encoding="utf-8")
        report_writer = csv.writer(report_file)
        report_writer.writerow(["FILA", "EXPEDIENTE", "MOTIVO", "SUBIDO"])

        # ── Open joined + clean report files BEFORE the loop (streaming writes + Ctrl+C protection) ──
        joined_csv_path = result_dir / "reporte_rechazadas.csv"
        joined_xlsx_path = result_dir / "reporte_rechazadas.xlsx"
        clean_csv_path = result_dir / "filas_rechazadas_para_corregir.csv"
        clean_xlsx_path = result_dir / "filas_rechazadas_para_corregir.xlsx"

        joined_csv_file = joined_csv_path.open("w", newline="", encoding="utf-8")
        jw = csv.writer(joined_csv_file)
        joined_headers = (
            ["FILA", "MOTIVO", "SUBIDO"]
            + [f"col_{i}" for i in range(119)]
        )
        jw.writerow(joined_headers)
        joined_csv_file.flush()

        clean_csv_file = clean_csv_path.open("w", newline="", encoding="utf-8-sig")
        cw = csv.writer(clean_csv_file, delimiter=";")

        wb_joined = openpyxl.Workbook()
        ws_joined = wb_joined.active
        ws_joined.title = "Rechazadas EDIF"
        ws_joined.append(joined_headers)

        wb_clean = openpyxl.Workbook()
        ws_clean = wb_clean.active
        ws_clean.title = "Para corregir EDIF"

        # Collect rejected rows for joined + clean reports
        rejected_rows: list[dict] = []

        rh_report_csv_path = result_dir / "reporte_ingesta_legacy_rh.csv"
        rh_report_xlsx_path = result_dir / "reporte_ingesta_legacy_rh.xlsx"
        rh_report_file = rh_report_csv_path.open("w", newline="", encoding="utf-8")
        rh_report_writer = csv.writer(rh_report_file)
        rh_report_headers = [
            "FILA", "NRO", "EXPEDIENTE", "LIQUIDACION_ID", "NUMERO_EDIFICACION",
            "SLOT", "ESPECIALIDAD", "CIP", "DELEGADO_LEGACY",
            "PERFIL_STATUS", "DELEGADO_STATUS", "OPERACION_STATUS",
            "LIQUIDACION_DELEGADO_STATUS", "DETALLE_HONORARIO_STATUS",
            "COMPROBANTE_STATUS", "REGISTRADO_EN_BD", "MOTIVO",
        ]
        rh_report_writer.writerow(rh_report_headers)

        # Process
        processed = 0
        rejected = 0
        skipped = 0
        skipped_by_date = 0
        errors = 0
        total_todas = 0
        error_details: list[str] = []

        # RH Phase 1 counters
        rh_rows_parsed = 0
        rh_slots_parsed = 0
        rh_slots_candidates = 0  # slots with delegate+CIP
        rh_slots_skipped_no_delegate = 0
        rh_slots_invalid_period_month = 0
        rh_comprobantes_parsed = 0
        rh_comprobantes_invalid = 0

        # Phase 2 counters (Delegado helpers — only when NOT dry_run)
        rh_perfiles_creados = 0
        rh_perfiles_reusados = 0
        rh_delegados_creados = 0
        rh_delegados_reusados = 0
        rh_operaciones_creadas = 0
        rh_operaciones_reusadas = 0
        rh_operaciones_conflicto = 0
        rh_operaciones_error = 0
        rh_slots_sin_especialidad = 0

        # Phase 3 counters (LiquidacionDelegado + DetalleHonorarioDelegado)
        rh_ld_creados = 0
        rh_ld_reusados = 0
        rh_ld_error = 0
        rh_ld_no_liquidacion = 0
        rh_ld_ambiguo = 0
        rh_dh_creados = 0
        rh_dh_reusados = 0
        rh_dh_error = 0

        # Phase 4 counters (LiquidacionComprobante)
        rh_comp_creados = 0
        rh_comp_actualizados = 0
        rh_comp_omitidos = 0
        rh_comp_errores = 0

        # ── Main loop with Ctrl+C protection ─────────────────────────────────
        try:
            for idx, row in enumerate(rows, start=2):  # row 2 onward (row 1 is header)
                # No ESPECIALIDAD filter — process ALL rows
                especialidad_raw = row[COL_ESPECIALIDAD]
                if especialidad_raw and str(especialidad_raw).strip().upper() == "TODAS":
                    total_todas += 1

                try:
                    if self.fecha_desde is not None:
                        fecha_row = _parse_fecha(row[COL_FECHA] if len(row) > COL_FECHA else None)
                        if fecha_row < self.fecha_desde:
                            skipped_by_date += 1
                            continue

                    # ── Skip si el numero ya existe ──────────────────────────────
                    id_raw = row[COL_ID] if len(row) > COL_ID else None
                    try:
                        id_val = int(float(str(id_raw).strip())) if id_raw is not None and str(id_raw).strip() != "" else None
                    except (ValueError, TypeError):
                        id_val = None
                    existing_edificacion = None
                    if id_val is not None:
                        existing_edificacion = (
                            LiquidacionEdificacion.objects.select_related("liquidacion")
                            .filter(numero=id_val)
                            .first()
                        )
                    if existing_edificacion is not None:
                        skipped += 1
                        self._log(self.style.WARNING(
                            f"  EXISTENTE row {idx}: numero {id_val} ya existe; procesando RH/delegados"
                        ))

                    # ── Rechazo: NRO == 0 (filas anómalas, no se suben) ──────────
                    nro_raw = row[1] if len(row) > 1 else None
                    try:
                        nro_val = int(float(str(nro_raw).strip())) if nro_raw is not None and str(nro_raw).strip() != "" else None
                    except (ValueError, TypeError):
                        nro_val = None
                    if nro_val == 0:
                        rejected_rows.append({"fila": idx, "row": row, "motivo": "NRO == 0", "subido": "NO"})
                        report_writer.writerow([idx, "", "NRO == 0", "NO"])
                        # ── Live write to joined CSV + Excel ─────────────────────────
                        jw.writerow([idx, "NRO == 0", "NO"] + row)
                        joined_csv_file.flush()
                        ws_joined.append([idx, "NRO == 0", "NO"] + row)
                        ws_clean.append(row)
                        rejected += 1
                        self._log(self.style.WARNING(f"  RECHAZADO row {idx}: NRO == 0"))
                        continue

                    # ── Rechazo: DPTOPRDI vacío (distrito obligatorio) ──────────
                    dptoprdri = row[COL_DPTOPRDI]
                    if dptoprdri is None or str(dptoprdri).strip() == "":
                        rejected_rows.append({"fila": idx, "row": row, "motivo": "Distrito vacío (DPTOPRDI)", "subido": "NO"})
                        report_writer.writerow([idx, "", "Distrito vacío (DPTOPRDI)", "NO"])
                        # ── Live write to joined CSV + Excel ─────────────────────────
                        jw.writerow([idx, "Distrito vacío (DPTOPRDI)", "NO"] + row)
                        joined_csv_file.flush()
                        ws_joined.append([idx, "Distrito vacío (DPTOPRDI)", "NO"] + row)
                        ws_clean.append(row)
                        rejected += 1
                        self._log(self.style.WARNING(f"  RECHAZADO row {idx}: DPTOPRDI vacío"))
                        continue

                    # Build payload
                    payload, anomalies, _ = self._build_payload(row, idx, orchestrator)

                    # ── Filtro opcional: rechazar diferencia alta ──────────────
                    # Compara el subtotal legacy (Excel) contra el subtotal recalculado
                    # real (sin override). Solo sube si la diferencia <= umbral.
                    if self.rechazar_dif_alta:
                        excel_subtotal = (
                            payload.cotizacion_legacy.sub_total
                            if payload.cotizacion_legacy is not None
                            else None
                        )
                        recal_subtotal = None
                        if excel_subtotal is not None:
                            try:
                                recal = orchestrator.cotizar_legacy_proceso(payload)
                                recal_subtotal = recal.total_subtotal
                            except Exception:  # noqa: BLE001
                                recal_subtotal = None
                        if (
                            excel_subtotal is not None
                            and recal_subtotal is not None
                            and abs(excel_subtotal - recal_subtotal) > self.umbral_dif
                        ):
                            diff = abs(excel_subtotal - recal_subtotal)
                            motivo = f"Diferencia alta subtotal: legacy={excel_subtotal}, recalc={recal_subtotal}, diff={diff} > {self.umbral_dif}"
                            rejected_rows.append({"fila": idx, "row": row, "motivo": motivo, "subido": "NO"})
                            report_writer.writerow([
                                idx,
                                payload.liquidacion_general.expediente or "",
                                motivo,
                                "NO",
                            ])
                            # ── Live write to joined CSV + Excel ─────────────────────────
                            jw.writerow([idx, motivo, "NO"] + row)
                            joined_csv_file.flush()
                            ws_joined.append([idx, motivo, "NO"] + row)
                            ws_clean.append(row)
                            rejected += 1
                            continue

                    # Get usuario from USUARIO column (per-row)
                    usuario_raw = row[COL_USUARIO] if len(row) > COL_USUARIO else None
                    usuario = _get_or_create_usuario_from_usuario(usuario_raw)

                    created_liquidacion_general = existing_edificacion.liquidacion if existing_edificacion is not None else None
                    if not self.dry_run and created_liquidacion_general is None:
                        created_result = orchestrator.crear_legacy_proceso(
                            usuario_id=usuario.id,
                            payload=payload,
                        )
                        created_liquidacion_general = LiquidacionGeneral.objects.get(
                            id=created_result.liquidacion_general.id
                        )

                    processed += 1

                    # ── Phase 1: RH slot parsing (no DB writes) ─────────────────────
                    rh_rows_parsed += 1
                    comprobante = _parse_comprobante(row)
                    if comprobante["raw"] is not None:
                        # Has a value — count as seen; invalid if neither serie nor numero parsed
                        rh_comprobantes_parsed += 1
                        if comprobante["serie"] is None and comprobante["numero"] is None:
                            rh_comprobantes_invalid += 1
                    else:
                        # No NROFACTURA at all
                        rh_comprobantes_invalid += 1

                    # ── Row-level Phase 2+3 resolution (only when NOT dry_run) ─────────
                    tipo_liq_edificacion = None
                    liquidacion_row = None  # same-row LiquidacionGeneral (shared by all slots)
                    row_municipalidad = None  # municipalidad for this row (same for all slots)
                    row_comprobante_status = ""

                    if not self.dry_run:
                        # Pre-resolve TipoLiquidacion once per row
                        tipo_liq_edificacion = (
                            TipoLiquidacionModel.objects.filter(codigo=TipoLiquidacion.EDIFICACION).first()
                        )

                        # ── Phase 3: Find same-row LiquidacionGeneral ─────────────────
                        expediente = payload.liquidacion_general.expediente
                        nrorev_raw = row[COL_NROREV] if len(row) > COL_NROREV else None
                        try:
                            numero_revision = int(float(str(nrorev_raw).strip())) if nrorev_raw and str(nrorev_raw).strip() else None
                        except (ValueError, TypeError):
                            numero_revision = None

                        # Resolve municipalidad for this row (used for same-row lookup)
                        codpago_raw = row[COL_CODPAGO] if len(row) > COL_CODPAGO else None
                        codpago_str = str(codpago_raw).strip().upper() if codpago_raw is not None else ""
                        if codpago_str:
                            row_municipalidad = (
                                Municipalidad.objects.filter(codigo=codpago_str).first()
                            )

                        if created_liquidacion_general is not None:
                            liquidacion_row = created_liquidacion_general
                        elif row_municipalidad is not None and numero_revision is not None:
                            liquidacion_row, liq_status = _find_same_row_liquidacion(
                                expediente, numero_revision, row_municipalidad
                            )
                            if liq_status == "NO_ENCONTRADO":
                                rh_ld_no_liquidacion += 1
                            elif liq_status == "AMBIGUO":
                                rh_ld_ambiguo += 1

                        # Parse monetary data for this row (shared by all slots' details)
                        monetary = _parse_row_monetary(row)

                        # ── Phase 4: Upsert LiquidacionComprobante ─────────────────────
                        total = _parse_total(row)
                        if liquidacion_row is not None:
                            comp, comp_status = _upsert_liquidacion_comprobante(
                                liquidacion=liquidacion_row,
                                comprobante_data=comprobante,
                                total=total,
                                dry_run=self.dry_run,
                            )
                            if comp_status == "CREADO":
                                rh_comp_creados += 1
                            elif comp_status == "ACTUALIZADO":
                                rh_comp_actualizados += 1
                            elif comp_status == "OMITIDO":
                                rh_comp_omitidos += 1
                            else:
                                rh_comp_errores += 1
                            row_comprobante_status = comp_status

                    # Slot loop ────────────────────────────────────────────────────────
                    row_any_delegado_created = False
                    row_skip_motivo = ""
                    slots_with_delegate_candidate = 0  # Phase 1 succeeded (slot_data not None)
                    all_cip_slots_failed = True  # Pessimistic: assume fail unless Phase 2 proves otherwise (write mode only)
                    slots_with_cip = 0  # Slots with non-empty CIP (for Case B vs Case A distinction)
                    slots_with_nonempty_delegate = 0  # Slots with non-empty delegate (Phase 2 would attempt CIP resolution)
                    for slot_num in range(1, 5):
                        rh_slots_parsed += 1
                        slot_data = _parse_rh_slot(row, slot_num)
                        if slot_data is None:
                            rh_slots_skipped_no_delegate += 1
                            if not row_skip_motivo:
                                row_skip_motivo = "Sin delegado: liquidación creada, RH omitido"
                            continue
                        rh_slots_candidates += 1
                        slots_with_delegate_candidate += 1
                        # Track slots with non-empty delegate (Phase 2 would attempt CIP resolution)
                        if slot_data["delegado"]:
                            slots_with_nonempty_delegate += 1
                        # Track slots with non-empty CIP (for Case B vs Case A distinction)
                        if slot_data["cip"]:
                            slots_with_cip += 1
                        # Invalid period/month: periodo present but mes absent/invalid
                        if slot_data["periodo"] is not None and slot_data["mes"] is None:
                            rh_slots_invalid_period_month += 1

                        # ── Phase 2: Ensure PerfilIngeniero/Delegado/DelegadoOperacion ──
                        # Only when NOT dry_run (i.e., LiquidacionGeneral is being created).
                        if not self.dry_run:
                            perfil_status = ""
                            del_status = ""
                            op_status = ""
                            ld_status = ""
                            dh_status = ""
                            rh_registered = False
                            rh_motivo = ""

                            def _write_rh_report_row():
                                numero_edificacion = ""
                                if liquidacion_row is not None:
                                    edificacion = getattr(liquidacion_row, "edificaciones", None)
                                    numero_edificacion = getattr(edificacion, "numero", "") if edificacion else ""
                                rh_report_writer.writerow([
                                    idx,
                                    row[COL_NRO] if len(row) > COL_NRO else "",
                                    payload.liquidacion_general.expediente or "",
                                    str(liquidacion_row.id) if liquidacion_row is not None else "",
                                    numero_edificacion,
                                    slot_num,
                                    slot_data.get("specialty"),
                                    slot_data.get("cip"),
                                    slot_data.get("delegado"),
                                    perfil_status,
                                    del_status,
                                    op_status,
                                    ld_status,
                                    dh_status,
                                    row_comprobante_status,
                                    "SI" if rh_registered else "NO",
                                    rh_motivo,
                                ])

                            if row_municipalidad is None:
                                rh_motivo = "Municipalidad no encontrada para la fila"
                                _write_rh_report_row()
                                continue

                            # Ensure PerfilIngeniero by CIP — only if delegate is present
                            if not slot_data["delegado"]:
                                # Delegate is empty — skip Phase 2 entirely
                                rh_slots_skipped_no_delegate += 1
                                rh_motivo = "Sin delegado: liquidación creada, RH omitido"
                                if not row_skip_motivo:
                                    row_skip_motivo = "Sin delegado: liquidación creada, RH omitido"
                                _write_rh_report_row()
                                continue

                            # Delegate present: resolve CIP
                            perfil, perfil_status = _ensure_perfil_ingeniero_by_cip(
                                slot_data["cip"], dry_run=self.dry_run
                            )
                            if perfil is None:
                                # Case B: CIP was provided but does not resolve — track but continue
                                all_cip_slots_failed = True
                                rh_motivo = f"CIP no resuelto: {slot_data['cip']}"
                                row_skip_motivo = f"CIP no resuelto: {slot_data['cip']}"
                                _write_rh_report_row()
                                continue
                            # CIP resolved successfully for this slot
                            all_cip_slots_failed = False
                            if perfil_status == "CREADO_DESDE_CIP":
                                rh_perfiles_creados += 1
                            else:
                                rh_perfiles_reusados += 1

                            # Resolve EspecialidadRevision for this slot
                            especialidad_rev = _resolve_slot_especialidad_revision(slot_num)
                            if especialidad_rev is None:
                                rh_slots_sin_especialidad += 1
                                rh_motivo = "EspecialidadRevision no encontrada para el slot"
                                _write_rh_report_row()
                                continue

                            # Ensure Delegado for the perfil
                            delegado, del_status = _ensure_delegado_for_perfil(
                                perfil, dry_run=self.dry_run
                            )
                            if delegado is None:
                                rh_motivo = f"Delegado no disponible: {del_status}"
                                _write_rh_report_row()
                                continue
                            if del_status == "CREADO":
                                rh_delegados_creados += 1
                            else:
                                rh_delegados_reusados += 1

                            # Use pre-resolved TipoLiquidacion (EDIFICACION)
                            tipo_liq = tipo_liq_edificacion

                            # Ensure DelegadoOperacion
                            operacion, op_status = _ensure_delegado_operacion(
                                delegado=delegado,
                                municipalidad=row_municipalidad,
                                tipo_liquidacion=tipo_liq,
                                especialidad_revision=especialidad_rev,
                                dry_run=self.dry_run,
                            )
                            if op_status == "CREADO":
                                rh_operaciones_creadas += 1
                            elif op_status == "YA_EXISTE":
                                rh_operaciones_reusadas += 1
                            elif op_status == "CONFLICTO":
                                rh_operaciones_conflicto += 1
                            else:
                                rh_operaciones_error += 1

                            # ── Phase 3: Ensure LiquidacionDelegado ──────────────────
                            if liquidacion_row is not None:
                                ld, ld_status = _ensure_liquidacion_delegado(
                                    liquidacion=liquidacion_row,
                                    delegado=delegado,
                                    especialidad_revision=especialidad_rev,
                                    delegado_operacion=operacion,
                                    slot_data=slot_data,
                                    dry_run=self.dry_run,
                                )
                                if ld_status == "CREADO":
                                    rh_ld_creados += 1
                                elif ld_status == "YA_EXISTE":
                                    rh_ld_reusados += 1
                                else:
                                    rh_ld_error += 1

                                # ── Phase 3: Ensure DetalleHonorarioDelegado ───────────
                                if ld is not None and ld_status == "CREADO":
                                    dh, dh_status = _ensure_detalle_honorario_delegado(
                                        liquidacion_delegado=ld,
                                        monetary=monetary,
                                        dry_run=self.dry_run,
                                    )
                                    if dh_status == "CREADO":
                                        rh_dh_creados += 1
                                        rh_registered = True
                                        row_any_delegado_created = True
                                    elif dh_status == "YA_EXISTE":
                                        rh_dh_reusados += 1
                                        rh_registered = True
                                        row_any_delegado_created = True
                                    else:
                                        rh_dh_error += 1
                                        rh_motivo = f"DetalleHonorarioDelegado status: {dh_status}"

                            _write_rh_report_row()

                    # ── "PARCIAL" block: runs after slot loop, handles both dry-run and write mode ─
                    # Case A: slot_data None (no delegate) → PARCIAL
                    # Case B: all slots with CIP failed to resolve → NO (reject row)
                    if not row_any_delegado_created:
                        if slots_with_delegate_candidate == 0:
                            # Case A: all slots had no CIP/delegate (Phase 1 skip for all slots)
                            fallback_motivo = "Sin delegado: liquidación creada, RH omitido"
                            reporte_subido = "PARCIAL"
                        elif all_cip_slots_failed and slots_with_nonempty_delegate > 0:
                            # Case B: had slots with CIP but ALL failed to resolve → reject
                            fallback_motivo = row_skip_motivo or "CIP no resuelto"
                            reporte_subido = "NO"
                            rejected_rows.append({
                                "fila": idx,
                                "row": row,
                                "motivo": fallback_motivo,
                                "subido": "NO",
                            })
                            # ── Live write to joined CSV + Excel ─────────────────────────
                            jw.writerow([idx, fallback_motivo, "NO"] + row)
                            joined_csv_file.flush()
                            ws_joined.append([idx, fallback_motivo, "NO"] + row)
                            ws_clean.append(row)
                            rejected += 1
                            self._log(self.style.WARNING(
                                f"  RECHAZADO row {idx}: {fallback_motivo}"
                            ))
                        else:
                            # Should not happen: slots had candidates but none succeeded
                            fallback_motivo = row_skip_motivo or "Sin delegado: liquidación creada, RH omitido"
                            reporte_subido = "PARCIAL"
                        report_writer.writerow([
                            idx,
                            payload.liquidacion_general.expediente or "",
                            fallback_motivo,
                            reporte_subido,
                        ])

                    if anomalies:
                        for a in anomalies:
                            rejected_rows.append({"fila": idx, "row": row, "motivo": a, "subido": "SI" if not self.dry_run else "DRY"})
                            report_writer.writerow([idx, payload.liquidacion_general.expediente or "", a, "SI" if not self.dry_run else "DRY"])
                            # ── Live write to joined CSV + Excel ─────────────────────────
                            jw.writerow([idx, a, "SI" if not self.dry_run else "DRY"] + row)
                            joined_csv_file.flush()
                            ws_joined.append([idx, a, "SI" if not self.dry_run else "DRY"] + row)
                            ws_clean.append(row)
                    if processed % self.batch_size == 0:
                        self._log(f"  Checkpoint: {processed}/{total_rows} rows processed")
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    rejected_rows.append({"fila": idx, "row": row, "motivo": f"ERROR: {exc}", "subido": "NO"})
                    codpago = row[COL_CODPAGO] if len(row) > COL_CODPAGO else None
                    msg = f"Row {idx} (CODPAGO={str(codpago)!r}): {exc}"
                    error_details.append(msg)
                    report_writer.writerow([idx, "", f"ERROR: {exc}", "NO"])
                    # ── Live write to joined CSV + Excel ─────────────────────────
                    jw.writerow([idx, f"ERROR: {exc}", "NO"] + row)
                    joined_csv_file.flush()
                    ws_joined.append([idx, f"ERROR: {exc}", "NO"] + row)
                    ws_clean.append(row)
                    self._log(self.style.ERROR(f"  ERROR row {idx}: {exc}"))
                    if options.get("traceback"):
                        import traceback

                        self._log(traceback.format_exc())

            report_file.close()
            rh_report_file.close()

        except KeyboardInterrupt:
            self._log(self.style.WARNING(
                "\n[!] Proceso cancelado forzadamente por el usuario. Interrumpiendo ingesta..."
            ))
        finally:
            # ── Close CSV files and save Excel workbooks (Ctrl+C safe) ─────────
            try:
                report_file.close()
            except Exception:
                pass
            try:
                rh_report_file.close()
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
                self._log(f"  Saved wb_joined XLSX: {joined_xlsx_path}")
            except Exception as exc:
                self._log(self.style.WARNING(f"  Error saving wb_joined XLSX: {exc}"))
            try:
                wb_clean.save(str(clean_xlsx_path))
                self._log(f"  Saved wb_clean XLSX: {clean_xlsx_path}")
            except Exception as exc:
                self._log(self.style.WARNING(f"  Error saving wb_clean XLSX: {exc}"))
            self._log(f"  Joined/clean report files saved.")

        # RH XLSX (from pre-loop RH CSV)
        rh_wb = openpyxl.Workbook()
        rh_ws = rh_wb.active
        rh_ws.title = "RH"
        with rh_report_csv_path.open("r", newline="", encoding="utf-8") as rh_csv_file:
            for row_data in csv.reader(rh_csv_file):
                rh_ws.append(row_data)
        rh_wb.save(str(rh_report_xlsx_path))

        # Summary report
        self._log(self.style.SUCCESS("\n=== REPORTE DE IMPORTACION LEGACY ==="))
        self._log(f"  Total filas 'TODAS': {total_todas}")
        self._log(f"  Procesadas (subidas): {processed}")
        self._log(f"  Rechazadas (NRO==0 o distrito vacío): {rejected}")
        self._log(f"  Saltadas (ya existentes):              {skipped}")
        if self.fecha_desde is not None:
            self._log(f"  Saltadas por fecha:                    {skipped_by_date}")
        self._log(f"  Errores: {errors}")
        self._log(f"  Reportes en {result_dir}:")
        self._log(f"    reporte_ingesta_legacy.csv")
        self._log(f"    reporte_rechazadas.csv + .xlsx")
        self._log(f"    filas_rechazadas_para_corregir.csv + .xlsx")
        self._log(f"  Reporte RH CSV: {rh_report_csv_path}")
        self._log(f"  Reporte RH XLSX: {rh_report_xlsx_path}")

        if error_details:
            self._log(self.style.WARNING("\n  Error details (first 20):"))
            for detail in error_details[:20]:
                self._log(f"    {detail}")
            if len(error_details) > 20:
                self._log(f"    ... and {len(error_details) - 20} more errors")

        # ── Phase 1 RH Report (parser scaffolding — no DB writes) ────────────────
        if self.dry_run_rh:
            self._log(self.style.SUCCESS("\n=== RH DELEGADO SLOT PARSE REPORT (Phase 1) ==="))
            self._log(f"  Rows with NROFACTURA parsed:        {rh_comprobantes_parsed}")
            self._log(f"  Rows with invalid NROFACTURA:       {rh_comprobantes_invalid}")
            self._log(f"  Total slots parsed (1..4):           {rh_slots_parsed}")
            self._log(f"  Slots with delegate+CIP (candidates): {rh_slots_candidates}")
            self._log(f"  Slots skipped (no delegate/CIP):     {rh_slots_skipped_no_delegate}")
            self._log(f"  Slots with invalid period/month:     {rh_slots_invalid_period_month}")
            if rh_rows_parsed > 0:
                self._log(f"  Average slots per row:              {rh_slots_parsed / rh_rows_parsed:.2f}")
            self._log(self.style.WARNING(
                "\n  NOTE: This is Phase 1 parser scaffolding only. "
                "No RH/Delegado/Comprobante records have been written."
            ))

        # ── Phase 2 RH Report (Delegado helpers — DB writes when NOT dry_run) ───
        total_ops = (
            rh_operaciones_creadas + rh_operaciones_reusadas +
            rh_operaciones_conflicto + rh_operaciones_error
        )
        if not self.dry_run:
            self._log(self.style.SUCCESS("\n=== RH DELEGADO HELPERS REPORT (Phase 2) ==="))
            self._log(f"  Perfiles creados (PerfilIngeniero):    {rh_perfiles_creados}")
            self._log(f"  Perfiles reusados:                    {rh_perfiles_reusados}")
            self._log(f"  Delegados creados:                     {rh_delegados_creados}")
            self._log(f"  Delegados reusados:                   {rh_delegados_reusados}")
            self._log(f"  Operaciones creadas:                   {rh_operaciones_creadas}")
            self._log(f"  Operaciones reusadas:                 {rh_operaciones_reusadas}")
            self._log(f"  Operaciones conflicto:                 {rh_operaciones_conflicto}")
            self._log(f"  Operaciones error:                    {rh_operaciones_error}")
            self._log(f"  Slots sin especialidad:               {rh_slots_sin_especialidad}")
            if total_ops > 0:
                self._log(
                    f"  Total operaciones procesadas:           {total_ops}"
                )
        elif rh_operaciones_creadas + rh_operaciones_reusadas > 0:
            # dry_run mode with Phase 2 helper activity — report what would happen
            self._log(self.style.WARNING("\n=== RH DELEGADO HELPERS REPORT (Phase 2 — DRY RUN) ==="))
            self._log(f"  Perfiles que serían creados:           {rh_perfiles_creados}")
            self._log(f"  Perfiles ya existentes:               {rh_perfiles_reusados}")
            self._log(f"  Delegados que serían creados:         {rh_delegados_creados}")
            self._log(f"  Delegados ya existentes:             {rh_delegados_reusados}")
            self._log(f"  Operaciones que serían creadas:       {rh_operaciones_creadas}")
            self._log(f"  Operaciones ya existentes:           {rh_operaciones_reusadas}")
            self._log(f"  Conflictos (reusados con warning):   {rh_operaciones_conflicto}")
            self._log(f"  Slots sin especialidad:             {rh_slots_sin_especialidad}")
            self._log(self.style.WARNING(
                "\n  NOTE: DRY-RUN — Phase 2 helpers are report-only; no records written."
            ))

        # ── Phase 3 RH Report (LiquidacionDelegado + DetalleHonorarioDelegado) ─────
        total_ld = rh_ld_creados + rh_ld_reusados + rh_ld_error
        total_dh = rh_dh_creados + rh_dh_reusados + rh_dh_error
        if not self.dry_run:
            self._log(self.style.SUCCESS("\n=== RH LIQUIDACION DELEGADO + DETALLE REPORT (Phase 3) ==="))
            self._log(f"  LiquidacionDelegado creados:            {rh_ld_creados}")
            self._log(f"  LiquidacionDelegado reusados:          {rh_ld_reusados}")
            self._log(f"  LiquidacionDelegado errores:           {rh_ld_error}")
            self._log(f"  LiquidacionDelegado sin liquidacion:  {rh_ld_no_liquidacion}")
            self._log(f"  LiquidacionDelegado ambigüo:          {rh_ld_ambiguo}")
            self._log(f"  DetalleHonorarioDelegado creados:     {rh_dh_creados}")
            self._log(f"  DetalleHonorarioDelegado reusados:   {rh_dh_reusados}")
            self._log(f"  DetalleHonorarioDelegado errores:    {rh_dh_error}")
            if total_ld > 0:
                self._log(f"  Total LiquidacionDelegado:              {total_ld}")
            if total_dh > 0:
                self._log(f"  Total DetalleHonorarioDelegado:        {total_dh}")
        elif total_ld + total_dh > 0:
            # dry_run mode with Phase 3 activity — report what would happen
            self._log(self.style.WARNING("\n=== RH LIQUIDACION DELEGADO + DETALLE REPORT (Phase 3 — DRY RUN) ==="))
            self._log(f"  LiquidacionDelegado que serían creados: {rh_ld_creados}")
            self._log(f"  LiquidacionDelegado ya existentes:    {rh_ld_reusados}")
            self._log(f"  LiquidacionDelegado errores:         {rh_ld_error}")
            self._log(f"  LiquidacionDelegado sin liquidacion: {rh_ld_no_liquidacion}")
            self._log(f"  LiquidacionDelegado ambigüo:       {rh_ld_ambiguo}")
            self._log(f"  DetalleHonorarioDelegado creados:   {rh_dh_creados}")
            self._log(f"  DetalleHonorarioDelegado reusados: {rh_dh_reusados}")
            self._log(f"  DetalleHonorarioDelegado errores:  {rh_dh_error}")
            self._log(self.style.WARNING(
                "\n  NOTE: DRY-RUN — Phase 3 helpers are report-only; no records written."
            ))

        # ── Phase 4 RH Report (LiquidacionComprobante) ─────────────────────────────
        total_comp = rh_comp_creados + rh_comp_actualizados + rh_comp_errores
        if not self.dry_run:
            self._log(self.style.SUCCESS("\n=== RH COMPROBANTE REPORT (Phase 4) ==="))
            self._log(f"  Comprobantes creados:                 {rh_comp_creados}")
            self._log(f"  Comprobantes actualizados:            {rh_comp_actualizados}")
            self._log(f"  Comprobantes omitidos (sin NROFACTURA): {rh_comp_omitidos}")
            self._log(f"  Comprobantes errores:                {rh_comp_errores}")
            if total_comp > 0:
                self._log(f"  Total comprobantes procesadas:        {total_comp}")
        elif total_comp > 0:
            self._log(self.style.WARNING("\n=== RH COMPROBANTE REPORT (Phase 4 — DRY RUN) ==="))
            self._log(f"  Comprobantes que serían creados:     {rh_comp_creados}")
            self._log(f"  Comprobantes que serían actualizados: {rh_comp_actualizados}")
            self._log(f"  Comprobantes omitidos:              {rh_comp_omitidos}")
            self._log(f"  Comprobantes errores:              {rh_comp_errores}")
            self._log(self.style.WARNING(
                "\n  NOTE: DRY-RUN — Phase 4 helpers are report-only; no records written."
            ))

        # Always regenerate the detailed report (CSV + XLSX) after importing
        self._log(self.style.SUCCESS("\n  Generando reporte detallado (CSV + XLSX)..."))
        self._generar_reporte_detallado(rows, orchestrator, data_path.parent)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, msg):
        """Write a message, handling Windows encoding quirks."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            safe = msg.encode("ascii", "replace").decode("ascii")
            self.stdout.write(safe)

    def _generar_reporte_detallado(self, rows: list, orchestrator, output_dir: Path) -> Path:
        """
        Generate the detailed legacy report (CSV + XLSX) comparing Excel values
        vs calculated values for EVERY row. Does NOT touch the database.

        Uses the same _build_payload (with explicit tarifa for NROREV>1) so the
        report matches what the import stores. Writes:
            <output_dir>/reporte_legacy_detallado.csv
            <output_dir>/reporte_legacy_detallado.xlsx
        """
        headers = [
            "FILA", "NRO", "EXPEDIENTE", "FECHA_REGISTRO", "ESPECIALIDAD",
            "RAZON_SOCIAL", "VALOR_OBRA",
            "PORCENTAJE_EXCEL", "PORCENTAJE_CALCULADO",
            "SUBTOTAL_EXCEL", "SUBTOTAL_CALCULADO",
            "TOTAL_EXCEL", "TOTAL_CALCULADO",
            "DESCRIPCION_LEGACY", "ESTADO", "REGISTRADO_EN_BD",
        ]
        csv_path = output_dir / "reporte_legacy_detallado.csv"
        xlsx_path = output_dir / "reporte_legacy_detallado.xlsx"

        out_file = csv_path.open("w", newline="", encoding="utf-8")
        writer = csv.writer(out_file)
        writer.writerow(headers)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Detalle"
        ws.append(headers)

        counts = {"OK": 0, "AVISO": 0, "RECHAZADO": 0, "ERROR": 0}

        for idx, row in enumerate(rows, start=2):
            fila = idx
            estado = "ERROR"
            anomalies: list[str] = []

            def col(r, n):
                return r[n] if len(r) > n else None

            nro_raw = col(row, COL_NRO)
            try:
                nro_val = int(float(str(nro_raw).strip())) if nro_raw is not None and str(nro_raw).strip() != "" else None
            except (ValueError, TypeError):
                nro_val = None

            dptoprdri = col(row, COL_DPTOPRDI)
            razon_social = col(row, COL_RAZONSOCIAL) or col(row, COL_NOMBRE) or ""
            especialidad_str = str(col(row, COL_ESPECIALIDAD) or "").strip()

            # ── RECHAZADO ──────────────────────────────────────────────
            if nro_val == 0 or (dptoprdri is None or str(dptoprdri).strip() == ""):
                estado = "RECHAZADO"
                if nro_val == 0:
                    anomalies.append("NRO == 0")
                if dptoprdri is None or str(dptoprdri).strip() == "":
                    anomalies.append("Distrito vacío (DPTOPRDI)")
                row_data = [
                    fila, nro_val if nro_val is not None else "", "", "", especialidad_str,
                    razon_social, col(row, COL_VALOROBRA) or "",
                    col(row, COL_PORCENTAJE) or "", "",
                    col(row, COL_SUBTOTAL) or "", "",
                    col(row, COL_TOTAL) or "", "",
                    ", ".join(anomalies), estado,
                    False,
                ]
                writer.writerow(row_data)
                ws.append([str(v) if v is not None else "" for v in row_data])
                counts[estado] += 1
                continue

            try:
                payload, row_anomalies, _ = self._build_payload(row, idx, orchestrator)
                anomalies = row_anomalies

                excel_total_raw = col(row, COL_TOTAL)
                excel_subtotal_raw = col(row, COL_SUBTOTAL)
                excel_pct_raw = col(row, COL_PORCENTAJE)
                excel_total = Decimal(str(excel_total_raw)) if excel_total_raw is not None else None
                excel_subtotal = Decimal(str(excel_subtotal_raw)) if excel_subtotal_raw is not None else None
                excel_pct = Decimal(str(excel_pct_raw)) if excel_pct_raw is not None else None

                cotizacion = orchestrator.cotizar_legacy_proceso(payload)
                pct_calculado = cotizacion.porcentaje_liquidacion * Decimal(100) if cotizacion else None
                calc_total = cotizacion.total if cotizacion else None
                calc_subtotal = cotizacion.total_subtotal if cotizacion else None

                if cotizacion is not None:
                    if excel_total is not None and cotizacion.total != excel_total:
                        anomalies.append("Total no coincide con cálculo")
                    if excel_subtotal is not None and cotizacion.total_subtotal != excel_subtotal:
                        anomalies.append("Subtotal no coincide con cálculo")
                    if excel_pct is not None and pct_calculado is not None and pct_calculado != excel_pct:
                        anomalies.append("Porcentaje no coincide con cálculo")

                registrado_en_bd = True
                if (
                    self.rechazar_dif_alta
                    and excel_subtotal is not None
                    and calc_subtotal is not None
                    and abs(excel_subtotal - calc_subtotal) > self.umbral_dif
                ):
                    diff = abs(excel_subtotal - calc_subtotal)
                    anomalies.append(
                        f"Diferencia alta subtotal: legacy={excel_subtotal}, "
                        f"recalc={calc_subtotal}, diff={diff} > {self.umbral_dif}"
                    )
                    estado = "RECHAZADO"
                    registrado_en_bd = False
                else:
                    estado = "AVISO" if anomalies else "OK"
                counts[estado] += 1

                nroexpdte = col(row, COL_NROEXPDTE)
                expediente = str(nroexpdte).strip() if nroexpdte else None
                if not expediente or expediente.upper() == "NULL":
                    expediente = None

                fecha_raw = col(row, COL_FECHA)
                fecha_str = ""
                if fecha_raw:
                    try:
                        fecha_str = _parse_fecha(fecha_raw).isoformat()
                    except ValueError:
                        anomalies.append(f"Fecha inválida: {fecha_raw}")

                row_data = [
                    fila,
                    nro_val if nro_val is not None else "",
                    expediente,
                    fecha_str,
                    especialidad_str,
                    razon_social,
                    col(row, COL_VALOROBRA) or "",
                    excel_pct,
                    pct_calculado,
                    excel_subtotal,
                    calc_subtotal,
                    excel_total,
                    calc_total,
                    ", ".join(anomalies),
                    estado,
                    registrado_en_bd,
                ]
                writer.writerow(row_data)
                ws.append([str(v) if v is not None else "" for v in row_data])
            except VarianceError as e:
                estado = "ERROR"
                counts[estado] += 1
                row_data = [
                    fila,
                    nro_val if nro_val is not None else "",
                    "", "", especialidad_str,
                    razon_social,
                    col(row, COL_VALOROBRA) or "",
                    col(row, COL_PORCENTAJE) or "", "",
                    col(row, COL_SUBTOTAL) or "", str(e.subtotal_calculado) if e.subtotal_calculado is not None else "",
                    col(row, COL_TOTAL) or "", str(e.total_calculado) if e.total_calculado is not None else "",
                    f"ERROR: {e}", estado, False,
                ]
                writer.writerow(row_data)
                ws.append([str(v) if v is not None else "" for v in row_data])
            except Exception as exc:  # noqa: BLE001
                estado = "ERROR"
                counts[estado] += 1
                row_data = [
                    fila,
                    nro_val if nro_val is not None else "",
                    "", "", especialidad_str,
                    razon_social,
                    col(row, COL_VALOROBRA) or "",
                    col(row, COL_PORCENTAJE) or "", "",
                    col(row, COL_SUBTOTAL) or "", "",
                    col(row, COL_TOTAL) or "", "",
                    f"ERROR: {exc}", estado, False,
                ]
                writer.writerow(row_data)
                ws.append([str(v) if v is not None else "" for v in row_data])

        out_file.close()
        wb.save(str(xlsx_path))

        self._log(f"\n=== REPORTE LEGACY DETALLADO ===")
        self._log(f"  Total filas procesadas: {len(rows)}")
        for k in ("OK", "AVISO", "RECHAZADO", "ERROR"):
            self._log(f"  {k}: {counts[k]}")
        self._log(f"  CSV: {csv_path}")
        self._log(f"  XLSX: {xlsx_path}")
        return csv_path

    def _read_csv(self, path: Path) -> list:
        """
        Read a CSV file with ';' delimiter and BOM UTF-8 encoding.

        Header is in row 1, data rows are 2..N.
        Returns a list of rows (each row is a list of string cell values).
        """
        with path.open("r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=";")
            rows = []
            for i, row in enumerate(reader):
                if i == 0:
                    continue  # skip header
                rows.append(row)
        return rows

    def _build_payload(self, row: list, idx: int, orchestrator) -> tuple:
        """
        Build a LiquidacionEdificacionesLegacyIn from an Excel row list.

        Returns (payload, anomalies_list, unit_ambiguity).
        Raises ValueError on parse errors (converted to str in the caller's except).
        """
        anomalies = []

        # ── Null checks ────────────────────────────────────────────────────────
        def _check_null(col_idx: int, col_name: str):
            val = row[col_idx]
            if val is None:
                anomalies.append(f"NULL en columna {col_name}")
                return True
            if str(val).strip().upper() == "NULL":
                anomalies.append(f"NULL en columna {col_name}")
                return True
            return False

        _check_null(COL_CODPAGO, "CODPAGO")
        _check_null(COL_DNI, "DNI")
        _check_null(COL_NOMBRE, "NOMBRE")
        _check_null(COL_DIRECCION, "DIRECCION")
        _check_null(COL_VALOROBRA, "VALOROBRA")
        _check_null(COL_FECHA, "FECHA")
        _check_null(COL_TOTAL, "TOTAL")
        _check_null(COL_SUBTOTAL, "SUBTOTAL")
        _check_null(COL_PORCENTAJE, "PORCENTAJE")
        _check_null(COL_NROREV, "NROREV")

        # ── Encoding issues ───────────────────────────────────────────────────
        for col_idx, col_name in [(COL_NOMBRE, "NOMBRE"), (COL_DIRECCION, "DIRECCION"), (COL_PROYECTO, "PROYECTO")]:
            val = row[col_idx]
            if val is not None and "�" in str(val):
                anomalies.append("Encoding issue en texto")

        # ── Especialidad ─────────────────────────────────────────────────────
        especialidad_raw = row[COL_ESPECIALIDAD]
        especialidad_str = str(especialidad_raw).strip() if especialidad_raw else ""
        valid_esp = {"TODAS", "Estructuras", "Inst. Sanitarias", "Inst. Mecánico Eléctricas"}
        if especialidad_str and especialidad_str not in valid_esp:
            anomalies.append(f"Especialidad no estándar: {especialidad_str}")

        # Log especialidad for this row (not wired to DB)
        if especialidad_str:
            logger.debug("Row %d: ESPECIALIDAD=%s", idx, especialidad_str)

        # ── Entidad (documento) ───────────────────────────────────────────────
        dni_raw = row[COL_DNI]
        ruc_raw = row[COL_RUC]
        dni_str = str(dni_raw).strip() if dni_raw else ""
        ruc_str = str(ruc_raw).strip() if ruc_raw else ""

        # Solo es anomalía si faltan AMBOS. Si hay DNI o RUC, está bien
        # (el tipo_documento lo determina).
        if not dni_str and not ruc_str:
            anomalies.append("Sin documento (DNI y RUC faltantes)")

        tipo_documento, numero_documento = _resolve_tipo_documento(dni_raw)

        # ── RUC as fallback ──────────────────────────────────────────────────
        if not dni_str and ruc_str:
            tipo_documento = "RUC"
            numero_documento = ruc_str

        # ── municipalidad ─────────────────────────────────────────────────────
        codpago = row[COL_CODPAGO]
        codpago_str = str(codpago).strip().upper() if codpago is not None else ""
        if not codpago_str:
            # CODPAGO no es necesario — no es error fatal, se anota y se usa fallback
            anomalies.append("CodPago faltante")
            municipalidad = Municipalidad.objects.first()
            if not municipalidad:
                raise ValueError("No hay municipalidades en la base de datos")
        else:
            try:
                municipalidad = Municipalidad.objects.get(codigo=codpago_str)
            except ObjectDoesNotExist:
                anomalies.append(f"CodPago no encontrado: {codpago_str}")
                municipalidad = Municipalidad.objects.first()
                if not municipalidad:
                    raise ValueError(f"No se encontró municipalidad para {codpago_str!r} y no hay fallback")

        municipalidad_id = municipalidad.id

        # ── distrito: prefer the FK id to avoid one DB lookup per report row ──
        distrito_id = getattr(municipalidad, "distrito_id", None)
        if distrito_id:
            pass
        else:
            dptoprdri = row[COL_DPTOPRDI]
            distrito_nombre = str(dptoprdri).split("/")[-1].strip() if dptoprdri else ""
            distrito_nombre, provincia_nombre = _normalizar_distrito(distrito_nombre)
            distrito_qs = UbigeoDistrito.objects.filter(nombre__iexact=distrito_nombre)
            if provincia_nombre:
                distrito_qs = distrito_qs.filter(provincia__nombre__iexact=provincia_nombre)
            distrito = distrito_qs.first()
            if distrito is not None and getattr(distrito, "id", None):
                distrito_id = distrito.id
            else:
                fallback = UbigeoDistrito.objects.first()
                if fallback:
                    distrito_id = fallback.id
                    anomalies.append(f"Distrito no encontrado: {distrito_nombre}")
                    self._log(self.style.WARNING(f"  WARNING: Distrito {distrito_nombre!r} not found, fallback to {fallback.nombre} (id={fallback.id})"))
                else:
                    raise ValueError("No UbigeoDistrito records found in database")

        # ── Proyecto ─────────────────────────────────────────────────────────
        # El campo del proyecto es razon_social. El Excel trae NOMBRE (col4) y
        # RAZONSOCIAL (col15). Usamos RAZONSOCIAL con fallback a NOMBRE.
        razon_social = row[COL_RAZONSOCIAL]
        if razon_social is None or str(razon_social).strip() == "":
            razon_social = row[COL_NOMBRE]
        if razon_social is None or str(razon_social).strip() == "":
            raise ValueError("RAZONSOCIAL/NOMBRE is empty")
        razon_social_str = str(razon_social).strip()

        direccion = row[COL_DIRECCION]
        if direccion is None or str(direccion).strip() == "":
            raise ValueError("DIRECCION is empty")
        direccion_str = str(direccion).strip()

        # ── Expediente ────────────────────────────────────────────────────────
        nroexpdte = row[COL_NROEXPDTE]
        expediente = str(nroexpdte).strip() if nroexpdte else None
        if not expediente or expediente.upper() == "NULL":
            expediente = None
        if expediente is None:
            anomalies.append("Expediente faltante")

        # ── Fecha de registro ────────────────────────────────────────────────
        fecha_raw = row[COL_FECHA]
        try:
            fecha_registro = _parse_fecha(fecha_raw)
        except ValueError as exc:
            anomalies.append(f"Fecha inválida: {fecha_raw}")
            raise ValueError(f"Invalid FECHA {fecha_raw!r}: {exc}") from exc

        # ── Valor de obra ────────────────────────────────────────────────────
        valor_raw = row[COL_VALOROBRA]
        if valor_raw is None or str(valor_raw).strip() == "":
            raise ValueError("VALOROBRA is empty")
        try:
            valor_declarado = Decimal(str(valor_raw).strip())
        except (InvalidOperation, ValueError) as exc:
            anomalies.append(f"ValorObra inválido o cero: {valor_raw}")
            raise ValueError(f"Invalid VALOROBRA {valor_raw!r}: {exc}") from exc

        if valor_declarado <= 0:
            anomalies.append(f"ValorObra inválido o cero: {valor_raw}")
            raise ValueError(f"VALOROBRA must be positive, got {valor_declarado}")

        # ── Numero revision from NROREV ───────────────────────────────────────
        nrorev_raw = row[COL_NROREV]
        nrorev_val = None
        if nrorev_raw is not None and str(nrorev_raw).strip() != "":
            try:
                nrorev_val = int(float(str(nrorev_raw).strip()))
            except (ValueError, TypeError):
                nrorev_val = None

        if nrorev_val is None:
            anomalies.append("NROREV faltante — se asigna 1")
            nrorev_val = 1
        elif nrorev_val > MAX_REVISIONES:
            anomalies.append(f"NROREV anómalo: {nrorev_val}")

        # ── denominacion_de_proyecto from PROYECTO ─────────────────
        proyecto_raw = row[COL_PROYECTO]
        proyecto_str = str(proyecto_raw).strip() if proyecto_raw else ""
        denominacion_de_proyecto = proyecto_str if proyecto_str else None
        if not proyecto_str:
            anomalies.append("PROYECTO vacío — se usa None")

        # ── numero (legacy ID from source CSV col 0) ─────────────────────────
        # Read ID from col 0 and set as numero to preserve the historical legacy ID.
        # AutoNumeroModel.save() respects a non-None numero (no auto-increment).
        # The orchestrator's skip check uses LiquidacionEdificacion.objects.filter(numero=id_val).
        id_raw = row[COL_ID] if len(row) > COL_ID else None
        try:
            id_val = int(float(str(id_raw).strip())) if id_raw is not None and str(id_raw).strip() != "" else None
        except (ValueError, TypeError):
            id_val = None
        numero = id_val

        # ── Contacto (TFONO + TPERSONA) ──────────────────────────────────────
        tpersona_raw = row[COL_TPERSONA] if len(row) > COL_TPERSONA else None
        tfono_raw = row[COL_TFONO] if len(row) > COL_TFONO else None

        nombres, apellidos = _parse_tpersona(tpersona_raw)
        telefono = str(tfono_raw).strip() if tfono_raw is not None and str(tfono_raw).strip() != "" and str(tfono_raw).strip().upper() != "NULL" else None

        contacto_inline = None
        has_nombres = nombres is not None and nombres != ""
        has_telefono = telefono is not None and telefono != ""

        if has_nombres or has_telefono:
            # Only create contacto if we have at least one useful field
            if has_nombres:
                contacto_inline = ContactoInlineSchema(
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                )
            elif has_telefono:
                # TFONO present but TPERSONA empty — can't create contacto without nombre
                anomalies.append("TFONO presente sin TPERSONA — contacto no creado")

        # ── Pre-calculation comparison ────────────────────────────────────────
        # Build minimal payload for cotizar_legacy_proceso (partial, just for calculation)
        # We need to build the full payload first to call cotizar_legacy_proceso
        proyecto_schema = ProyectoCotizarSchema(
            nombre_propietario=razon_social_str,
            direccion=direccion_str,
            distrito_id=distrito_id,
            entidad=EntidadInlineSchema(
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                razon_social=razon_social_str,
            ),
        )

        liquidacion_general_partial = LiquidacionGeneralLegacyIn(
            municipalidad_id=municipalidad_id,
            expediente=expediente,
            observacion=None,
            retencion=False,
            proyecto=proyecto_schema,
            contacto=contacto_inline,
            fecha_registro=fecha_registro,
            denominacion_de_proyecto=denominacion_de_proyecto,
            descripcion_legacy=None,  # Will be set after comparison
        )

        # ── Tarifas explícitas para especialidad concreta ──
        # En legacy la tarifa NO viene en el Excel: se resuelve la vigente a
        # fecha_registro (igual que el flujo normal) y se combina SOLO con la
        # especialidad revisada de la fila -> porcentaje parcial de esa tarifa.
        # Solo ESPECIALIDAD == TODAS -> auto-fill (tarifas=[]).
        tarifas_explicit: list[LiquidacionPorcentajeObraTarifaIn] = []
        if especialidad_str and especialidad_str.strip().upper() != "TODAS":
            esp_revision = _resolve_especialidad_revision(especialidad_str)
            if esp_revision is None:
                anomalies.append(f"Especialidad no encontrada: {especialidad_str}")
            else:
                tarifas_vigentes = orchestrator.legacy_po_core.get_tarifa_por_fecha(
                    TipoLiquidacion.EDIFICACION, fecha_registro
                )
                if not tarifas_vigentes:
                    anomalies.append("No hay tarifa vigente para la fecha — se usa auto-fill")
                else:
                    tarifas_dedup = list({t.tarifa_base_id: t for t in tarifas_vigentes}.values())
                    tarifas_explicit = [
                        LiquidacionPorcentajeObraTarifaIn(
                            tarifa_porcentaje_obra_id=t.id,
                            especialidad_id=esp_revision.id,
                        )
                        for t in tarifas_dedup
                    ]

        liquidacion_especifica = LiquidacionPorcentajeObraIn(
            datos=LiquidacionPorcentajeObraDatosIn(valor_declarado=valor_declarado),
            tarifas=tarifas_explicit,  # Vacío = auto-fill; con entries = porcentaje parcial
        )

        # Subtotal/total legacy: se guardan los montos del Excel (fuente de verdad),
        # el porcentaje se recalcula con la tarifa vigente en el servicio.
        cotizacion_legacy = None
        if (
            row[COL_SUBTOTAL] is not None
            and row[COL_TOTAL] is not None
            and str(row[COL_SUBTOTAL]).strip() != ""
            and str(row[COL_TOTAL]).strip() != ""
        ):
            try:
                cotizacion_legacy = CotizacionLegacyIn(
                    sub_total=Decimal(str(row[COL_SUBTOTAL]).strip()),
                    total=Decimal(str(row[COL_TOTAL]).strip()),
                )
            except (InvalidOperation, ValueError) as exc:
                anomalies.append(f"Subtotal/Total inválido: {exc}")

        payload = LiquidacionEdificacionesLegacyIn(
            liquidacion_general=liquidacion_general_partial,
            liquidacion_especifica=liquidacion_especifica,
            cotizacion_legacy=cotizacion_legacy,
            numero_revision=nrorev_val,
            numero=numero,
        )

        # ── Pre-calculate (cotizar) ──────────────────────────────────────────
        unit_ambiguity = False
        try:
            cotizacion = orchestrator.cotizar_legacy_proceso(payload)
        except HttpError as exc:
            # Cotizar failed — log and continue (row still gets inserted without pre-calculation comparison)
            logger.warning("Cotizar failed for row %d: %s", idx, exc)
            cotizacion = None

        if cotizacion is not None:
            # Compare totals (exact, no tolerance)
            excel_total_raw = row[COL_TOTAL]
            excel_total = Decimal(str(excel_total_raw)) if excel_total_raw is not None else None
            if excel_total is not None and cotizacion.total != excel_total:
                anomalies.append("Total no coincide con cálculo")

            # Compare subtotals (exact)
            excel_subtotal_raw = row[COL_SUBTOTAL]
            excel_subtotal = Decimal(str(excel_subtotal_raw)) if excel_subtotal_raw is not None else None
            if excel_subtotal is not None and cotizacion.total_subtotal != excel_subtotal:
                anomalies.append("Subtotal no coincide con cálculo")

            # Compare porcentaje — exact (no tolerance).
            # Excel PORCENTAJE is a percentage number (0.15 = 15%).
            # cotizacion.porcentaje_liquidacion is a FRACTION (0.0015 = 0.15%).
            # So: porcentaje_liquidacion * 100 == PORCENTAJE.
            excel_pct_raw = row[COL_PORCENTAJE]
            excel_pct = Decimal(str(excel_pct_raw)) if excel_pct_raw is not None else None
            if excel_pct is not None:
                pct_calculado = cotizacion.porcentaje_liquidacion * Decimal(100)
                if pct_calculado != excel_pct:
                    anomalies.append("Porcentaje no coincide con cálculo")

        # ── Build descripcion_legacy ─────────────────────────────────────────
        descripcion_legacy = ", ".join(anomalies) if anomalies else None

        # Update payload with descripcion_legacy
        payload.liquidacion_general.descripcion_legacy = descripcion_legacy

        return payload, anomalies, unit_ambiguity
