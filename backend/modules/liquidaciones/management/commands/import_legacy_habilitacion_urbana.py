"""
Management command to import legacy habilitación urbana data from a CSV file.

Usage:
    python manage.py import_legacy_habilitacion_urbana --settings=config.settings.development
    python manage.py import_legacy_habilitacion_urbana --dry-run --settings=config.settings.development
    python manage.py import_legacy_habilitacion_urbana --solo-reporte --settings=config.settings.development

Source file:
    backend/core_application/seeds/historico/HU_ALL.csv
    (61 columns, delimiter ';', BOM UTF-8, FECHA "YYYY-MM-DD HH:MM:SS")

Input columns (openpyxl 0-indexed after list(row)):
    ID=0, NRO=1, RUC=2, NOMBRE=3, PROYECTO=4, DPTOPRDI=5, DIRECCION=6, URBNZCION=7,
    PROYECTISTA=8, AREA=9, DELEGADO=10, SUBTOTAL=11, IGV=12, TOTAL=13, FECHA=14,
    DNI=15, RAZONSOCIAL=16, CODPAGO=17, NROFACTURA=18, PORCENTAJE=19, NROEXPDTE=20,
    IMPBRUTO=21, APORCODEMU=22, FONDOCOMUN=23, HONORARIO=24, IMPUESRENTA=25,
    NETOHONORA=26, USUARIO=27, IMPRESO=28, DOC=29, FECHAPRES=30, NROORDEN=31,
    FECHAREVI=32, DICTAMEN=33, MES=34, PERIODO=35, NRORECIBO=36, FECHARECIBO=37,
    NROMEMO=38, OBSERVA=39, TDNI=40, TFONO=41, TPERSONA=42, MSUELOS=43,
    DIFERENCIA=44, NROREV=45, TASAIGV=46, PERIODELE=47, RENTACIP=48, FECOMPRO=49,
    NRONC=50, NROQRPLZA=51, DSCTO=52, RUCDIRECC=53, RETENCION=54, CIP=55,
    BLKDEL=56, NROCHEQUE=57, CONCEPTO=58, REINTEGRO=59, DOCCOM=60

Output:
    Creates LiquidacionHabilitacionUrbana records via
    LiquidacionHabilitacionUrbanaLegacyOrchestrator.crear_legacy_proceso().

Key differences from edificaciones:
    - HU has 1 delegate slot (not 4)
    - HU delegates always use EspecialidadRevision "Ingeniería Civil"
    - NROREV=1 or 3 (not >5 like edificaciones)
    - Cotizacion bypass uses SUBTOTAL/TOTAL directly
    - tarifa_m2_id resolved by fecha_registro via legacy_m2_core
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


from modules.entidades.domain.models.municipalidad import (
    Municipalidad,
)
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
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_legacy.liquidacion_habilitacion_urbana_legacy_orchestrator import (
    LiquidacionHabilitacionUrbanaLegacyOrchestrator,
)
from modules.liquidaciones.domain.resources import normalize_cip
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    EntidadInlineSchema,
    ProyectoCotizarSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_habilitacion_urbana_legacy_schemas import (
    CotizacionLegacyIn,
    LiquidacionGeneralLegacyIn,
    LiquidacionHabilitacionUrbanaLegacyIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionPorMetroCuadradoDatosIn,
    LiquidacionPorMetroCuadradoIn,
    LiquidacionPorMetroCuadradoTarifaIn,
)
from modules.usuarios.di import UsuariosModule
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero
from modules.usuarios.domain.models.usuario import Usuario
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import (
    PerfilIngenieroCoreService,
)

logger = logging.getLogger(__name__)

# Default path to legacy data file
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "core_application" / "seeds" / "historico" / "HU_ALL.csv"

# CSV column indices — 0-indexed (list from csv.reader)
# Header (row 1): ID=0 NRO=1 RUC=2 NOMBRE=3 PROYECTO=4 DPTOPRDI=5 DIRECCION=6 URBNZCION=7
# PROYECTISTA=8 AREA=9 DELEGADO=10 SUBTOTAL=11 IGV=12 TOTAL=13 FECHA=14 DNI=15
# RAZONSOCIAL=16 CODPAGO=17 NROFACTURA=18 PORCENTAJE=19 NROEXPDTE=20
# IMPBRUTO=21 APORCODEMU=22 FONDOCOMUN=23 HONORARIO=24 IMPUESRENTA=25 NETOHONORA=26
# USUARIO=27 IMPRESO=28 DOC=29 FECHAPRES=30 NROORDEN=31 FECHAREVI=32 DICTAMEN=33
# MES=34 PERIODO=35 NRORECIBO=36 FECHARECIBO=37 NROMEMO=38 OBSERVA=39
# TDNI=40 TFONO=41 TPERSONA=42 MSUELOS=43 DIFERENCIA=44 NROREV=45 TASAIGV=46
# PERIODELE=47 RENTACIP=48 FECOMPRO=49 NRONC=50 NROQRPLZA=51 DSCTO=52 RUCDIRECC=53
# RETENCION=54 CIP=55 BLKDEL=56 NROCHEQUE=57 CONCEPTO=58 REINTEGRO=59 DOCCOM=60
COL_ID = 0
COL_NRO = 1
COL_RUC = 2
COL_NOMBRE = 3
COL_PROYECTO = 4
COL_DPTOPRDI = 5
COL_DIRECCION = 6
COL_URBNZCION = 7
COL_PROYECTISTA = 8
COL_AREA = 9
COL_DELEGADO = 10
COL_SUBTOTAL = 11
COL_IGV = 12
COL_TOTAL = 13
COL_FECHA = 14
COL_DNI = 15
COL_RAZONSOCIAL = 16
COL_CODPAGO = 17
COL_NROFACTURA = 18
COL_PORCENTAJE = 19
COL_NROEXPDTE = 20
COL_IMPBRUTO = 21
COL_APORCODEMU = 22
COL_FONDOCOMUN = 23
COL_HONORARIO = 24
COL_IMPUESRENTA = 25
COL_NETOHONORA = 26
COL_USUARIO = 27
COL_IMPRESO = 28
COL_DOC = 29
COL_FECHAPRES = 30
COL_NROORDEN = 31
COL_FECHAREVI = 32
COL_DICTAMEN = 33
COL_MES = 34
COL_PERIODO = 35
COL_NRORECIBO = 36
COL_FECHARECIBO = 37
COL_NROMEMO = 38
COL_OBSERVA = 39
COL_TDNI = 40
COL_TFONO = 41
COL_TPERSONA = 42
COL_MSUELOS = 43
COL_DIFERENCIA = 44
COL_NROREV = 45
COL_TASAIGV = 46
COL_PERIODELE = 47
COL_RENTACIP = 48
COL_FECOMPRO = 49
COL_NRONC = 50
COL_NROQRPLZA = 51
COL_DSCTO = 52
COL_RUCDIRECC = 53
COL_RETENCION = 54
COL_CIP = 55
COL_BLKDEL = 56
COL_NROCHEQUE = 57
COL_CONCEPTO = 58
COL_REINTEGRO = 59
COL_DOCCOM = 60

# RH / Delegado column indices (single delegate slot for HU)
COL_DELGADO_CIP = COL_CIP  # 55 — separate CIP column
COL_DELEGADO_NOMBRE = COL_DELEGADO  # 10 — "CIP N-NOMBRE"
COL_PERIODO = COL_PERIODO  # 35
COL_MES = COL_MES  # 34
COL_FECHAPRES = COL_FECHAPRES  # 30
COL_FECHAREVI = COL_FECHAREVI  # 32
COL_NROORDEN = COL_NROORDEN  # 31
COL_DICTAMEN = COL_DICTAMEN  # 33
COL_NROMEMO = COL_NROMEMO  # 38 → maps to LiquidacionDelegado.numero_rh
COL_RENTACIP = COL_RENTACIP  # 48

# Shared monetary fields
COL_NETOHONORA = COL_NETOHONORA  # 26

# Comprobante
COL_NROFACTURA = COL_NROFACTURA  # 18


# ── Parsing helpers ──────────────────────────────────────────────────────────────


def _parse_fecha(raw) -> date:
    """Parse FECHA value (datetime object or string) -> date."""
    if not raw:
        raise ValueError("FECHA is empty")
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


# Mapeo regex → (nombre canónico de distrito, nombre de provincia) en UbigeoDistrito.
_DISTRITO_SINONIMOS: list[tuple[str, tuple[str, str | None]]] = [
    (r"^CERCADO\s+DE\s+LIMA$", ("LIMA", None)),
    (r"^CENTRO\s+HIST[OÓ]RICO\s+DE\s+LIMA$", ("LIMA", None)),
    (r"^LIMA\s+CERCADO\s+Y\s+PROVINCIAL\s+LIMA$", ("LIMA", None)),
    (r"^ATE\s+VITARTE$", ("ATE", None)),
    (r"^LURIGANCHO\s*[-–]\s*CHOSICA$", ("LURIGANCHO", None)),
    (r"^BARRANCA\s*[-–]\s*NORTE$", ("BARRANCA", None)),
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


def _build_orchestrator() -> LiquidacionHabilitacionUrbanaLegacyOrchestrator:
    """
    Build a fully-injected LiquidacionHabilitacionUrbanaLegacyOrchestrator.

    Creates a fresh Injector with the LiquidacionesModule and UsuariosModule
    bindings, then requests the orchestrator from the injector.
    """
    injector = Injector(
        [
            LiquidacionesModule(),
            UsuariosModule(),
        ]
    )
    return injector.get(LiquidacionHabilitacionUrbanaLegacyOrchestrator)


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


def _get_or_create_usuario_from_usuario(usuario_raw) -> Usuario:
    """
    Get or create a Usuario from a USUARIO raw value.

    If USUARIO is blank/empty, returns the system user (fallback).
    """
    username = _normalize_usuario_to_username(usuario_raw)
    if not username:
        return _get_or_create_system_user()

    existing = Usuario.objects.filter(username=username).first()
    if existing:
        return existing

    user = Usuario.objects.create(
        username=username,
        email=f"{username}@legacy.local",
        dni=None,
    )
    user.set_password("admin")
    user.save(using=Usuario.objects.db)
    logger.info("Created legacy user '%s' from USUARIO='%s'", username, usuario_raw)
    return user


# ── RH / Delegado helpers ───────────────────────────────────────────────────────


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
    """
    val = _coerce_int(raw)
    if val is None:
        return None
    if 1 <= val <= 12:
        return val
    return None


def _parse_delegado_slot(row: list) -> dict | None:
    """
    Parse single delegate slot from a HU row.

    Returns None if no delegate/CIP present (skip signal).

    Returns dict with:
        {
            "delegado": str or None,       # raw nombre from DELEGADO col 10
            "cip": int or None,            # from CIP col 55
            "periodo": int or None,        # PERIODO col 35
            "mes": int or None,            # 1..12 or None if invalid/absent (col 34)
            "fecha_presentacion": date or None,
            "fecha_revision": date or None,
            "nro_orden": int or None,      # NROORDEN col 31
            "dictamen": str or None,        # DICTAMEN col 33
            "numero_rh": str or None,       # NROMEMO col 38 → LiquidacionDelegado.numero_rh
            "monetary": dict,               # shared monetary fields
        }
    """
    def _col(idx):
        return row[idx] if len(row) > idx else None

    cip_raw = _col(COL_CIP)
    cip = _coerce_int(cip_raw)

    delegado_raw = _col(COL_DELEGADO)
    delegado_text = str(delegado_raw).strip() if delegado_raw is not None else None
    if not delegado_text or delegado_text.upper() == "NULL":
        return None

    if cip is None:
        return None

    periodo = _coerce_int(_col(COL_PERIODO))
    mes = _coerce_month(_col(COL_MES))

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
        return None

    # Parse monetary fields
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

    monetary = {
        "imp_bruto": _dec(_col(COL_IMPBRUTO)),
        "renta_cip": _dec(_col(COL_RENTACIP)),
        "aporte_codemu": _dec(_col(COL_APORCODEMU)),
        "fondo_comun": _dec(_col(COL_FONDOCOMUN)),
        "neto_honorario": _dec(_col(COL_NETOHONORA)),
        "subtotal": _dec(_col(COL_SUBTOTAL)),
    }

    # Decision: NROMEMO(38) → numero_rh (CharField, the only field available in LiquidacionDelegado)
    # NROMEMO is the RH memo/note number, stored as string in numero_rh
    nromemo_raw = _col(COL_NROMEMO)
    nromemo_str = str(nromemo_raw).strip() if nromemo_raw is not None and str(nromemo_raw).strip().upper() != "NULL" else None

    return {
        "delegado": delegado_text,
        "cip": cip,
        "periodo": periodo,
        "mes": mes,
        "fecha_presentacion": _parse_date(_col(COL_FECHAPRES)),
        "fecha_revision": _parse_date(_col(COL_FECHAREVI)),
        "nro_orden": _coerce_int(_col(COL_NROORDEN)),
        "dictamen": str(_col(COL_DICTAMEN)).strip() if _col(COL_DICTAMEN) is not None else None,
        "numero_rh": nromemo_str,
        "monetary": monetary,
    }


# ── Phase 2: RH Delegado helpers ────────────────────────────────────────────────


def _ensure_perfil_ingeniero_by_cip(cip: int, dry_run: bool = False) -> tuple[PerfilIngeniero | None, str]:
    """
    Get or create a PerfilIngeniero by normalized CIP, hydrating from CIP endpoint.

    Returns (perfil, status) where status is one of:
        "YA_EXISTE", "CREADO_DESDE_CIP", "ACTUALIZADO_DESDE_CIP",
        "SIN_COLEGIADO", "ERROR_CIP", "ERROR".
    """
    service = PerfilIngenieroCoreService()
    return service.hydrate_perfil_from_cip(str(cip), dry_run=dry_run)


def _ensure_delegado_for_perfil(
    perfil: PerfilIngeniero,
    dry_run: bool = False,
) -> tuple[Delegado | None, str]:
    """
    Get or create a Delegado for a PerfilIngeniero.

    Returns (delegado, status) where status is "CREADO", "YA_EXISTE", or "ERROR".
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
    municipalidad: type[Municipalidad],
    tipo_liquidacion: type[TipoLiquidacion],
    especialidad_revision,
    dry_run: bool = False,
) -> tuple[DelegadoOperacion | None, str]:
    """
    Get or create a DelegadoOperacion for a delegate/municipalidad/tipo_liquidacion.

    especialidad_revision must be the resolved "Ingeniería Civil" EspecialidadRevision
    (caller resolves it via _get_hu_especialidad_revision before calling this).

    Returns (operacion, status) where status is:
        "CREADO", "YA_EXISTE", "CONFLICTO", "ERROR".
    """
    if dry_run:
        existing = DelegadoOperacion.objects.filter(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            especialidad_revision=especialidad_revision,
        ).first()
        if existing is None:
            return None, "CREADO"
        return existing, "YA_EXISTE"

    try:
        existing = DelegadoOperacion.objects.filter(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            especialidad_revision=especialidad_revision,
        ).first()
        if existing:
            return existing, "YA_EXISTE"

        operation = DelegadoOperacion.objects.create(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            especialidad_revision=especialidad_revision,
            tipo=TipoDelegado.TITULAR,
        )
        return operation, "CREADO"
    except Exception:
        return None, "ERROR"


# ── Phase 4: LiquidacionComprobante helpers ─────────────────────────────────────


def _parse_comprobante(row: list) -> dict:
    """
    Parse NROFACTURA into serie and numero.

    Returns {"serie": str, "numero": str} or {"serie": None, "numero": None, "raw": str}.
    """
    raw = row[COL_NROFACTURA] if len(row) > COL_NROFACTURA else None
    if raw is None:
        return {"serie": None, "numero": None, "raw": None}
    text = str(raw).strip()
    if not text or text.upper() in ("NULL", ""):
        return {"serie": None, "numero": None, "raw": text}

    if "-" in text:
        parts = text.split("-", 1)
        serie = parts[0].strip()
        numero = parts[1].strip()
        return {"serie": serie, "numero": numero, "raw": text}

    return {"serie": None, "numero": text, "raw": text}


def _tipo_comprobante_from_nrofactura(raw: str | None) -> str | None:
    """
    Map NROFACTURA prefix to TipoComprobante value.

    Returns 'FACTURA' if raw starts with 'FAC', 'BOLETA' if raw starts with 'BOL'.
    """
    if not raw:
        return None
    upper = str(raw).strip().upper()
    if upper.startswith("FAC"):
        return "FACTURA"
    if upper.startswith("BOL"):
        return "BOLETA"
    return None


def _parse_total(row: list) -> Decimal | None:
    """Parse TOTAL column from a legacy row into a Decimal."""
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


def _upsert_liquidacion_comprobante(
    liquidacion: LiquidacionGeneral,
    comprobante_data: dict,
    total: Decimal | None,
    dry_run: bool = False,
) -> tuple[LiquidacionComprobante | None, str]:
    """
    Create or update a LiquidacionComprobante for a LiquidacionGeneral.

    Idempotency: finds existing active comprobante for this liquidation and
    updates it in-place rather than creating a duplicate.
    """
    raw_nrofactura = comprobante_data.get("raw")
    serie = comprobante_data.get("serie")
    numero = comprobante_data.get("numero")

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
            existing.serie = serie
            existing.numero = numero
            existing.tipo_comprobante = tipo
            existing.monto = total
            existing.save()
            return existing, "ACTUALIZADO"

        comp = LiquidacionComprobante.objects.create(
            liquidacion_general=liquidacion,
            tipo_comprobante=tipo,
            serie=serie,
            numero=numero,
            monto=total,
            activo=True,
        )
        return comp, "CREADO"
    except Exception:
        return None, "ERROR"


# ── Phase 3: LiquidacionDelegado + DetalleHonorarioDelegado helpers ───────────────


def _get_hu_especialidad_revision() -> tuple:
    """
    Resolve the EspecialidadRevision for Habilitación Urbana.

    HU always corresponds to "Ingeniería Civil" (same specialty used for
    slot 1 in edificaciones).  This is NOT nullable — the FK does not allow null.

    Returns (EspecialidadRevision, status) where status is:
        "ENCONTRADO"  — EspecialidadRevision resolved successfully
        "NO_ENCONTRADO" — "Ingeniería Civil" not found in BD; caller must reject the row
    """
    from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
    esp = EspecialidadRevision.objects.filter(nombre="Ingeniería Civil").first()
    if esp is None:
        return None, "NO_ENCONTRADO"
    return esp, "ENCONTRADO"


def _find_same_row_liquidacion(
    expediente: str | None,
    numero_revision: int,
    municipalidad: type[Municipalidad],
) -> tuple[LiquidacionGeneral | None, str]:
    """
    Find the LiquidacionGeneral created from the same legacy row.

    Uses (expediente, numero_revision, municipalidad, legacy=True).
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
        return None, "AMBIGUO"


def _ensure_liquidacion_delegado(
    liquidacion: LiquidacionGeneral,
    delegado: Delegado,
    especialidad_revision,
    delegado_operacion: DelegadoOperacion | None,
    slot_data: dict,
    dry_run: bool = False,
) -> tuple[LiquidacionDelegado | None, str]:
    """
    Get or create a LiquidacionDelegado for the given liquidation/delegado.

    especialidad_revision must be the resolved "Ingeniería Civil" EspecialidadRevision.
    Caller resolves it via _get_hu_especialidad_revision() — this function does NOT
    fall back to a placeholder; if it receives None, it returns RECHAZADO.

    Returns (liquidacion_delegado, status).
    """
    if especialidad_revision is None:
        return None, "RECHAZADO"

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
            numero_rh=slot_data.get("numero_rh"),
            dictamen_revision=slot_data.get("dictamen"),
        )
        return ld, "CREADO"
    except Exception:
        return None, "ERROR"


def _ensure_detalle_honorario_delegado(
    liquidacion_delegado: LiquidacionDelegado,
    monetary: dict,
    dry_run: bool = False,
) -> tuple[DetalleHonorarioDelegado | None, str]:
    """
    Get or create a DetalleHonorarioDelegado for a LiquidacionDelegado.

    Idempotency key: (liquidacion_delegado, recibo_mensual is null).
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
    except Exception:
        return None, "ERROR"


class Command(BaseCommand):
    help = "Import legacy habilitacion urbana data from CSV file via LiquidacionHabilitacionUrbanaLegacyOrchestrator"

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
            help="Umbral de diferencia (S/.) para --rechazar-dif-alta (default 1.0).",
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

    def _reset_liquidaciones(self) -> None:
        """Elimina TODAS las LiquidacionGeneral y los registros de finanzas asociados."""
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
                f"  [DRY-RUN] Se eliminarían {LiquidacionGeneral.objects.count()} LiquidacionGeneral"
            ))
            return

        DetalleHonorarioDelegado.objects.all().delete()
        DetalleHonorarioInspector.objects.all().delete()
        ReciboHonorarioDelegadoMensual.objects.all().delete()
        ReciboHonorarioInspectorMensual.objects.all().delete()
        ReciboHonorarioDelegado.objects.all().delete()
        ReciboHonorarioInspector.objects.all().delete()
        RegistroPagoInspector.objects.all().delete()
        deleted, _ = LiquidacionGeneral.objects.all().delete()
        self._log(f"  Eliminadas {deleted} filas (LiquidacionGeneral y relacionados).")

    def _log(self, msg):
        self.stdout.write(str(msg))

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
        Build a LiquidacionHabilitacionUrbanaLegacyIn from an Excel row list.

        Returns (payload, anomalies_list).

        Raises ValueError on parse errors (converted to str in the caller's except).
        """
        anomalies = []

        def _check_null(col_idx: int, col_name: str):
            val = row[col_idx]
            if val is None:
                anomalies.append(f"NULL en columna {col_name}")
                return True
            if str(val).strip().upper() == "NULL":
                anomalies.append(f"NULL en columna {col_name}")
                return True
            return False

        # Required fields check
        _check_null(COL_CODPAGO, "CODPAGO")
        _check_null(COL_FECHA, "FECHA")
        _check_null(COL_AREA, "AREA")

        # ── Entidad (documento) ───────────────────────────────────────────────
        dni_raw = row[COL_DNI]
        ruc_raw = row[COL_RUC]
        tipo_documento, numero_documento = _resolve_tipo_documento(dni_raw, ruc_raw)

        # ── municipalidad ─────────────────────────────────────────────────────
        codpago = row[COL_CODPAGO]
        codpago_str = str(codpago).strip().upper() if codpago is not None else ""
        if not codpago_str:
            anomalies.append("CodPago faltante")
            municipalidad = Municipalidad.objects.first()  # fallback
            if not municipalidad:
                raise ValueError("No hay municipalidades en la base de datos")
        else:
            try:
                municipalidad = Municipalidad.objects.get(codigo=codpago_str)
            except ObjectDoesNotExist:
                anomalies.append(f"CodPago no encontrado: {codpago_str}")
                municipalidad = Municipalidad.objects.first()
                if not municipalidad:
                    raise ValueError(f"No se encontró municipalidad para {codpago_str!r}")

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
            if distrito:
                distrito_id = distrito.id
            else:
                fallback = UbigeoDistrito.objects.first()
                if fallback:
                    distrito_id = fallback.id
                    anomalies.append(f"Distrito no encontrado: {distrito_nombre}")
                    self._log(self.style.WARNING(f"  WARNING: Distrito {distrito_nombre!r} not found, fallback to {fallback.nombre}"))
                else:
                    raise ValueError("No UbigeoDistrito records found in database")

        # ── Entidad / razon_social ────────────────────────────────────────────
        razon_social = row[COL_RAZONSOCIAL]
        if razon_social is None or str(razon_social).strip() == "":
            razon_social = row[COL_NOMBRE]
        if razon_social is None or str(razon_social).strip() == "":
            raise ValueError("RAZONSOCIAL/NOMBRE is empty")
        razon_social_str = str(razon_social).strip()

        # ── Entidad / nombre_propietario ──────────────────────────────────────
        nombre_propietario = row[COL_NOMBRE]
        if nombre_propietario is None or str(nombre_propietario).strip() == "":
            raise ValueError("NOMBRE is empty")
        nombre_propietario_str = str(nombre_propietario).strip()

        # ── Entidad / direccion ────────────────────────────────────────────────
        direccion = row[COL_DIRECCION]
        if direccion is None or str(direccion).strip() == "":
            raise ValueError("DIRECCION is empty")
        direccion_str = str(direccion).strip()

        # ── urbanizacion (from URBNZCION col 7) ───────────────────────────────
        urbanizacion_raw = row[COL_URBNZCION]
        urbanizacion = str(urbanizacion_raw).strip() if urbanizacion_raw is not None and str(urbanizacion_raw).strip().upper() != "NULL" else None

        # ── Expediente ─────────────────────────────────────────────────────────
        nroexpdte = row[COL_NROEXPDTE]
        expediente = str(nroexpdte).strip() if nroexpdte else None
        if not expediente or expediente.upper() == "NULL":
            expediente = None
        if expediente is None:
            anomalies.append("Expediente faltante")

        # ── Fecha de registro ─────────────────────────────────────────────────
        fecha_raw = row[COL_FECHA]
        try:
            fecha_registro = _parse_fecha(fecha_raw)
        except ValueError as exc:
            anomalies.append(f"Fecha inválida: {fecha_raw}")
            raise ValueError(f"Invalid FECHA {fecha_raw!r}: {exc}") from exc

        # ── Area ───────────────────────────────────────────────────────────────
        area_raw = row[COL_AREA]
        if area_raw is None or str(area_raw).strip() == "":
            raise ValueError("AREA is empty")
        try:
            area_solicitada = Decimal(str(area_raw).strip())
        except (InvalidOperation, ValueError) as exc:
            anomalies.append(f"Area inválida: {area_raw}")
            raise ValueError(f"Invalid AREA {area_raw!r}: {exc}") from exc

        if area_solicitada <= 0:
            anomalies.append(f"Area inválida o cero: {area_solicitada}")

        # ── Numero revision from NROREV ────────────────────────────────────────
        # HU: NROREV = 1 or 3 (only)
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
        elif nrorev_val not in (1, 3):
            anomalies.append(f"NROREV anómalo (esperado 1 o 3): {nrorev_val}")

        # ── denominacion_de_proyecto from PROYECTO ────────────────────────────
        proyecto_raw = row[COL_PROYECTO]
        proyecto_str = str(proyecto_raw).strip() if proyecto_raw else ""
        denominacion_de_proyecto = proyecto_str if proyecto_str else None
        if not proyecto_str:
            anomalies.append("PROYECTO vacío — se usa None")

        # ── retencion (bool from RETENCION col 54) ────────────────────────────
        retencion_raw = row[COL_RETENCION]
        retencion = False
        if retencion_raw is not None:
            retencion_text = str(retencion_raw).strip().upper()
            if retencion_text in ("SI", "SÍ", "1", "TRUE", "VERDADERO"):
                retencion = True
            elif retencion_text in ("NO", "0", "FALSE", "FALSO", ""):
                retencion = False

        # ── Contacto (TFONO + TPERSONA) ─────────────────────────────────────
        tpersona_raw = row[COL_TPERSONA] if len(row) > COL_TPERSONA else None
        tfono_raw = row[COL_TFONO] if len(row) > COL_TFONO else None

        nombres, apellidos = _parse_tpersona(tpersona_raw)
        telefono = str(tfono_raw).strip() if tfono_raw is not None and str(tfono_raw).strip() != "" and str(tfono_raw).strip().upper() != "NULL" else None

        contacto_inline = None
        has_nombres = nombres is not None and nombres != ""
        has_telefono = telefono is not None and telefono != ""

        if has_nombres or has_telefono:
            if has_nombres:
                contacto_inline = ContactoInlineSchema(
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                )
            elif has_telefono:
                anomalies.append("TFONO presente sin TPERSONA — contacto no creado")

        # ── Resolve tarifa_m2_id by fecha_registro ────────────────────────────
        # Use orchestrator.legacy_m2_core.get_tarifa_m2_por_fecha
        tarifa = orchestrator.legacy_m2_core.get_tarifa_m2_por_fecha(
            TipoLiquidacion.HABILITACION_URBANA, fecha_registro
        )
        if not tarifa:
            anomalies.append(f"No hay tarifa M2 HU para fecha {fecha_registro}")
            raise ValueError(f"No hay tarifa M2 HU para fecha {fecha_registro}")
        tarifa_m2_id = tarifa.id

        # ── Build proyecto schema ─────────────────────────────────────────────
        # Note: urbanizacion IS included in ProyectoCotizarSchema
        proyecto_schema = ProyectoCotizarSchema(
            nombre_propietario=nombre_propietario_str,
            direccion=direccion_str,
            urbanizacion=urbanizacion,
            distrito_id=distrito_id,
            entidad=EntidadInlineSchema(
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                razon_social=razon_social_str,
            ),
        )

        # ── Build liquidacion_general ─────────────────────────────────────────
        liquidacion_general = LiquidacionGeneralLegacyIn(
            municipalidad_id=municipalidad_id,
            expediente=expediente,
            observacion=None,
            retencion=retencion,
            proyecto=proyecto_schema,
            contacto=contacto_inline,
            fecha_registro=fecha_registro,
            denominacion_de_proyecto=denominacion_de_proyecto,
            descripcion_legacy=None,
        )

        # ── Build liquidacion_especifica ──────────────────────────────────────
        liquidacion_especifica = LiquidacionPorMetroCuadradoIn(
            datos=LiquidacionPorMetroCuadradoDatosIn(area_solicitada=area_solicitada),
            tarifa=LiquidacionPorMetroCuadradoTarifaIn(tarifa_m2_id=tarifa_m2_id),
        )

        # ── Subtotal/total legacy bypass ──────────────────────────────────────
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

        # ── numero (legacy ID from source CSV col 0) ──────────────────────────
        # Read ID from col 0 and set as numero to preserve the historical legacy ID.
        # AutoNumeroModel.save() respects a non-None numero (no auto-increment).
        id_raw = row[COL_ID] if len(row) > COL_ID else None
        try:
            id_val = int(float(str(id_raw).strip())) if id_raw is not None and str(id_raw).strip() != "" else None
        except (ValueError, TypeError):
            id_val = None

        # ── Build full payload ────────────────────────────────────────────────
        payload = LiquidacionHabilitacionUrbanaLegacyIn(
            liquidacion_general=liquidacion_general,
            liquidacion_especifica=liquidacion_especifica,
            cotizacion_legacy=cotizacion_legacy,
            numero_revision=nrorev_val,
            numero=id_val,
        )

        # ── Pre-calculate comparison (cotizar_legacy_proceso) ───────────────
        try:
            cotizacion = orchestrator.cotizar_legacy_proceso(payload)
        except HttpError as exc:
            logger.warning("Cotizar failed for row %d: %s", idx, exc)
            cotizacion = None

        if cotizacion is not None and cotizacion_legacy is not None:
            # Compare subtotals (SUBTOTAL Excel = neto, subtotal recalculated = neto)
            excel_subtotal = cotizacion_legacy.sub_total
            recalc_subtotal = cotizacion.subtotal  # after clamping
            if excel_subtotal is not None and abs(excel_subtotal - recalc_subtotal) > Decimal("0.01"):
                anomalies.append(f"Subtotal no coincide: excel={excel_subtotal}, recalc={recalc_subtotal}")

            # Compare totals (TOTAL Excel = bruto, total recalculated = bruto)
            excel_total = cotizacion_legacy.total
            recalc_total = cotizacion.total  # after clamping
            if excel_total is not None and abs(excel_total - recalc_total) > Decimal("0.01"):
                anomalies.append(f"Total no coincide: excel={excel_total}, recalc={recalc_total}")

        # ── Build descripcion_legacy ─────────────────────────────────────────
        descripcion_legacy = ", ".join(anomalies) if anomalies else None
        payload.liquidacion_general.descripcion_legacy = descripcion_legacy

        return payload, anomalies

    def _generar_reporte_detallado(self, rows: list, orchestrator, output_dir: Path) -> Path:
        """
        Generate the detailed legacy report (CSV + XLSX) comparing Excel values
        vs calculated values for EVERY row. Does NOT touch the database.
        """
        headers = [
            "FILA", "NRO", "EXPEDIENTE", "FECHA_REGISTRO",
            "NOMBRE_PROPIETARIO", "RAZON_SOCIAL",
            "AREA_SOLICITADA",
            "SUBTOTAL_EXCEL", "SUBTOTAL_CALCULADO",
            "TOTAL_EXCEL", "TOTAL_CALCULADO",
            "DESCRIPCION_LEGACY", "ESTADO",
        ]
        csv_path = output_dir / "reporte_legacy_detallado_hu.csv"
        xlsx_path = output_dir / "reporte_legacy_detallado_hu.xlsx"

        out_file = csv_path.open("w", newline="", encoding="utf-8")
        writer = csv.writer(out_file)
        writer.writerow(headers)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Detalle HU"
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
            nombre_raw = col(row, COL_NOMBRE) or ""
            razon_raw = col(row, COL_RAZONSOCIAL) or ""
            area_raw = col(row, COL_AREA) or ""

            if nro_val == 0 or (dptoprdri is None or str(dptoprdri).strip() == ""):
                estado = "RECHAZADO"
                if nro_val == 0:
                    anomalies.append("NRO == 0")
                if dptoprdri is None or str(dptoprdri).strip() == "":
                    anomalies.append("Distrito vacío (DPTOPRDI)")

            excel_total = None
            excel_subtotal = None
            calc_total = None
            calc_subtotal = None
            try:
                payload, row_anomalies = self._build_payload(row, idx, orchestrator)
                anomalies = row_anomalies

                excel_total_raw = col(row, COL_TOTAL)
                excel_subtotal_raw = col(row, COL_SUBTOTAL)
                excel_total = Decimal(str(excel_total_raw)) if excel_total_raw is not None else None
                excel_subtotal = Decimal(str(excel_subtotal_raw)) if excel_subtotal_raw is not None else None

                cotizacion = None
                try:
                    cotizacion = orchestrator.cotizar_legacy_proceso(payload)
                except HttpError:
                    pass

                calc_total = cotizacion.total if cotizacion else None
                calc_subtotal = cotizacion.subtotal if cotizacion else None

                estado = "OK" if not anomalies else "AVISO"
                if excel_total is not None and calc_total is not None and abs(excel_total - calc_total) > Decimal("0.01"):
                    estado = "AVISO"
                    anomalies.append(f"Total diff: excel={excel_total}, calc={calc_total}")

            except Exception as exc:
                estado = "ERROR"
                anomalies.append(str(exc))

            fecha_raw = col(row, COL_FECHA)
            expediente_raw = col(row, COL_NROEXPDTE) or ""

            row_data = [
                fila,
                nro_val if nro_val is not None else "",
                str(expediente_raw).strip(),
                str(fecha_raw).strip() if fecha_raw else "",
                str(nombre_raw).strip(),
                str(razon_raw).strip(),
                str(area_raw).strip(),
                str(excel_subtotal) if excel_subtotal is not None else "",
                str(calc_subtotal) if calc_subtotal is not None else "",
                str(excel_total) if excel_total is not None else "",
                str(calc_total) if calc_total is not None else "",
                ", ".join(anomalies),
                estado,
            ]
            writer.writerow(row_data)
            ws.append([str(v) if v is not None else "" for v in row_data])
            counts[estado] += 1

        wb.save(xlsx_path)
        out_file.close()

        self._log(f"\n  Reporte generado:")
        self._log(f"    CSV: {csv_path}")
        self._log(f"    XLSX: {xlsx_path}")
        self._log(f"  Estados: OK={counts['OK']}, AVISO={counts['AVISO']}, RECHAZADO={counts['RECHAZADO']}, ERROR={counts['ERROR']}")

        return csv_path

    def handle(self, *args, **options):
        self.dry_run = bool(options["dry_run"])
        self.batch_size = int(options["batch_size"])
        self.reset = bool(options.get("reset", False))
        self.solo_reporte = bool(options.get("solo_reporte", False))
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

        self._log("\n[import_legacy_habilitacion_urbana] Starting...")
        self._log(f"  Source: {data_path}")
        if self.fecha_desde is not None:
            self._log(self.style.WARNING(f"  --fecha-desde: procesando FECHA >= {self.fecha_desde}"))
        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE — no database writes"))

        # Build injector and resolve orchestrator
        self._log("  Resolving orchestrator...")
        orchestrator = _build_orchestrator()
        self._log("  Orchestrator ready.")

        # Read Excel
        rows = self._read_csv(data_path)
        limit = options.get("limit")
        if limit is not None:
            if limit < 1:
                raise CommandError("--limit debe ser mayor o igual a 1")
            rows = rows[:limit]
            self._log(self.style.WARNING(f"  --limit: procesando solo las primeras {limit} filas"))
        total_rows = len(rows)
        self._log(f"  Total rows to process: {total_rows}")

        # ── Solo reporte ─────────────────────────────────────────────────────
        if self.solo_reporte:
            self._log(self.style.WARNING("  --solo-reporte: NO se importa, solo se genera el detallado."))
            self._generar_reporte_detallado(rows, orchestrator, data_path.parent)
            return

        # Resolve system user for fallback
        system_user = _get_or_create_system_user()
        self._log(f"  System user fallback: username={system_user.username}")

        # Optional reset
        if self.reset:
            self._log(self.style.WARNING("  --reset: eliminando LiquidacionGeneral existentes..."))
            self._reset_liquidaciones()
            self._log(self.style.SUCCESS("  Reset completado."))

        # Each run writes to its own folder so migration reports are auditable.
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = Path(__file__).resolve().parents[5] / "result" / "HU" / run_id
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
            + [f"col_{i}" for i in range(61)]
        )
        jw.writerow(joined_headers)
        joined_csv_file.flush()

        clean_csv_file = clean_csv_path.open("w", newline="", encoding="utf-8-sig")
        cw = csv.writer(clean_csv_file, delimiter=";")

        wb_joined = openpyxl.Workbook()
        ws_joined = wb_joined.active
        ws_joined.title = "Rechazadas HU"
        ws_joined.append(joined_headers)

        wb_clean = openpyxl.Workbook()
        ws_clean = wb_clean.active
        ws_clean.title = "Para corregir HU"

        # Collect rejected rows for the joined + clean reports
        rejected_rows: list[dict] = []

        # Process counters
        processed = 0
        rejected = 0
        skipped = 0
        skipped_by_date = 0
        errors = 0

        # RH counters
        rh_rows_parsed = 0
        rh_slots_candidates = 0
        rh_slots_skipped_no_delegate = 0
        rh_comprobantes_parsed = 0
        rh_comprobantes_invalid = 0

        rh_perfiles_creados = 0
        rh_perfiles_reusados = 0
        rh_delegados_creados = 0
        rh_delegados_reusados = 0
        rh_operaciones_creadas = 0
        rh_operaciones_reusadas = 0
        rh_operaciones_error = 0

        rh_ld_creados = 0
        rh_ld_reusados = 0
        rh_ld_error = 0
        rh_ld_no_liquidacion = 0
        rh_ld_ambiguo = 0
        rh_dh_creados = 0
        rh_dh_reusados = 0
        rh_dh_error = 0

        rh_comp_creados = 0
        rh_comp_actualizados = 0
        rh_comp_omitidos = 0
        rh_comp_errores = 0

        # Pre-resolve TipoLiquidacion HU
        tipo_liq_hu = TipoLiquidacionModel.objects.filter(codigo=TipoLiquidacion.HABILITACION_URBANA).first()

        # ── Main loop ────────────────────────────────────────────────────────
        for idx, row in enumerate(rows, start=2):
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
                existing_habilitacion = None
                if id_val is not None:
                    existing_habilitacion = (
                        LiquidacionHabilitacionUrbana.objects.select_related("liquidacion")
                        .filter(numero=id_val)
                        .first()
                    )
                if existing_habilitacion is not None:
                    skipped += 1
                    self._log(self.style.WARNING(
                        f"  EXISTENTE row {idx}: numero {id_val} ya existe; procesando RH/delegados"
                    ))

                # ── Rechazo: NRO == 0 ────────────────────────────────────────
                nro_raw = row[COL_NRO] if len(row) > COL_NRO else None
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

                # ── Rechazo: DPTOPRDI vacío ────────────────────────────────
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
                payload, anomalies = self._build_payload(row, idx, orchestrator)

                # ── Filtro opcional: rechazar diferencia alta ──────────────
                if self.rechazar_dif_alta and payload.cotizacion_legacy is not None:
                    excel_subtotal = payload.cotizacion_legacy.sub_total
                    recal_subtotal = None
                    try:
                        recal = orchestrator.cotizar_legacy_proceso(payload)
                        recal_subtotal = recal.subtotal
                    except Exception:
                        recal_subtotal = None
                    if excel_subtotal is not None and recal_subtotal is not None and abs(excel_subtotal - recal_subtotal) > self.umbral_dif:
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

                # ── Pre-check CIP before creating liquidation (Case A/B) ──────────
                slot_data = _parse_delegado_slot(row)
                perfil_cache = None  # Will be set if we need to resolve CIP
                row_skip_motivo = ""

                if slot_data is None:
                    # Case A: no delegate/CIP — will create liquidation as PARCIAL
                    row_skip_motivo = "Sin delegado: liquidación creada, RH omitido"
                else:
                    # slot has CIP — resolve it BEFORE creating liquidation
                    perfil_cache, perfil_status = _ensure_perfil_ingeniero_by_cip(
                        slot_data["cip"], dry_run=self.dry_run
                    )
                    if perfil_cache is None:
                        # Case B: CIP provided but does not resolve — reject row entirely
                        motivo = f"CIP no resuelto: {slot_data['cip']}"
                        rejected_rows.append({"fila": idx, "row": row, "motivo": motivo, "subido": "NO"})
                        report_writer.writerow([idx, "", motivo, "NO"])
                        # ── Live write to joined CSV + Excel ─────────────────────────
                        jw.writerow([idx, motivo, "NO"] + row)
                        joined_csv_file.flush()
                        ws_joined.append([idx, motivo, "NO"] + row)
                        ws_clean.append(row)
                        rejected += 1
                        self._log(self.style.WARNING(f"  RECHAZADO row {idx}: {motivo}"))
                        continue

                # Get usuario from USUARIO column
                usuario_raw = row[COL_USUARIO] if len(row) > COL_USUARIO else None
                usuario = _get_or_create_usuario_from_usuario(usuario_raw)

                created_liquidacion_general = existing_habilitacion.liquidacion if existing_habilitacion is not None else None
                if not self.dry_run and created_liquidacion_general is None:
                    created_result = orchestrator.crear_legacy_proceso(
                        usuario_id=usuario.id,
                        payload=payload,
                    )
                    created_liquidacion_general = LiquidacionGeneral.objects.get(
                        id=created_result.liquidacion_general.id
                    )

                processed += 1
                rh_rows_parsed += 1

                # ── Phase post-creación: RH, Comprobante ──────────────────
                if not self.dry_run:
                    # Parse comprobante
                    comprobante = _parse_comprobante(row)
                    if comprobante["raw"] is not None:
                        rh_comprobantes_parsed += 1
                        if comprobante["serie"] is None and comprobante["numero"] is None:
                            rh_comprobantes_invalid += 1
                    else:
                        rh_comprobantes_invalid += 1

                    # ── Resolve row-level entities ──────────────────────────
                    expediente = payload.liquidacion_general.expediente
                    numero_revision = payload.numero_revision

                    # Resolve municipalidad
                    codpago_raw = row[COL_CODPAGO] if len(row) > COL_CODPAGO else None
                    codpago_str = str(codpago_raw).strip().upper() if codpago_raw is not None else ""
                    row_municipalidad = None
                    if codpago_str:
                        row_municipalidad = Municipalidad.objects.filter(codigo=codpago_str).first()

                    # Find same-row LiquidacionGeneral
                    liquidacion_row = None
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

                    # Parse monetary (shared for delegate detail)
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

                    monetary = {
                        "imp_bruto": _dec(row[COL_IMPBRUTO] if len(row) > COL_IMPBRUTO else None),
                        "renta_cip": _dec(row[COL_RENTACIP] if len(row) > COL_RENTACIP else None),
                        "aporte_codemu": _dec(row[COL_APORCODEMU] if len(row) > COL_APORCODEMU else None),
                        "fondo_comun": _dec(row[COL_FONDOCOMUN] if len(row) > COL_FONDOCOMUN else None),
                        "neto_honorario": _dec(row[COL_NETOHONORA] if len(row) > COL_NETOHONORA else None),
                        "subtotal": _dec(row[COL_SUBTOTAL] if len(row) > COL_SUBTOTAL else None),
                    }

                    # ── Phase 4: Upsert LiquidacionComprobante ─────────────
                    total = _parse_total(row)
                    comp_status = ""
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

                    # ── Single delegate slot for HU ─────────────────────────
                    expediente = payload.liquidacion_general.expediente
                    if slot_data is None:
                        rh_slots_skipped_no_delegate += 1
                        report_writer.writerow([
                            idx,
                            expediente or "",
                            "Sin delegado: liquidación creada, RH omitido",
                            "PARCIAL",
                        ])
                    else:
                        rh_slots_candidates += 1

                        if row_municipalidad is None:
                            self._log(self.style.WARNING(f"  Row {idx}: Municipalidad no encontrada"))
                        else:
                            # perfil already resolved above (Case B would have continued)
                            perfil = perfil_cache
                            perfil_status_resolved = ""  # already resolved pre-check
                            if perfil is None:
                                # Should not happen — Case B was handled before creation
                                self._log(self.style.WARNING(f"  Row {idx}: PerfilIngeniero no disponible"))
                                report_writer.writerow([
                                    idx,
                                    expediente or "",
                                    f"CIP no resuelto: {slot_data['cip']}",
                                    "NO",
                                ])
                            else:
                                if perfil_status == "CREADO_DESDE_CIP":
                                    rh_perfiles_creados += 1
                                else:
                                    rh_perfiles_reusados += 1

                                # Ensure Delegado for perfil
                                delegado, del_status = _ensure_delegado_for_perfil(
                                    perfil, dry_run=self.dry_run
                                )
                                if delegado is None:
                                    self._log(self.style.WARNING(f"  Row {idx}: Delegado no disponible: {del_status}"))
                                else:
                                    if del_status == "CREADO":
                                        rh_delegados_creados += 1
                                    else:
                                        rh_delegados_reusados += 1

                                    # Resolve EspecialidadRevision for HU — always "Ingeniería Civil"
                                    hu_esp, esp_status = _get_hu_especialidad_revision()
                                    if hu_esp is None:
                                        self._log(self.style.WARNING(
                                            f"  Row {idx}: EspecialidadRevision 'Ingeniería Civil' no encontrada en BD"
                                        ))
                                        rh_ld_error += 1
                                    else:
                                        # Ensure DelegadoOperacion with resolved especialidad
                                        operacion, op_status = _ensure_delegado_operacion(
                                            delegado=delegado,
                                            municipalidad=row_municipalidad,
                                            tipo_liquidacion=tipo_liq_hu,
                                            especialidad_revision=hu_esp,
                                            dry_run=self.dry_run,
                                        )
                                        if op_status == "CREADO":
                                            rh_operaciones_creadas += 1
                                        elif op_status == "YA_EXISTE":
                                            rh_operaciones_reusadas += 1
                                        else:
                                            rh_operaciones_error += 1

                                        # Ensure LiquidacionDelegado with resolved especialidad
                                        ld, ld_status = _ensure_liquidacion_delegado(
                                            liquidacion=liquidacion_row,
                                            delegado=delegado,
                                            especialidad_revision=hu_esp,
                                            delegado_operacion=operacion,
                                            slot_data=slot_data,
                                            dry_run=self.dry_run,
                                        )
                                        if ld is None:
                                            rh_ld_error += 1
                                        elif ld_status == "CREADO":
                                            rh_ld_creados += 1
                                        else:
                                            rh_ld_reusados += 1

                                        # Ensure DetalleHonorarioDelegado
                                        if ld is not None:
                                            dh, dh_status = _ensure_detalle_honorario_delegado(
                                                liquidacion_delegado=ld,
                                                monetary=slot_data.get("monetary", monetary),
                                                dry_run=self.dry_run,
                                            )
                                            if dh is None:
                                                rh_dh_error += 1
                                            elif dh_status == "CREADO":
                                                rh_dh_creados += 1
                                            else:
                                                rh_dh_reusados += 1

                # Progress checkpoint
                if processed % self.batch_size == 0:
                    self._log(f"  Progress: {processed}/{total_rows} rows processed...")

            except Exception as exc:
                errors += 1
                rejected_rows.append({"fila": idx, "row": row, "motivo": str(exc), "subido": "NO"})
                report_writer.writerow([idx, "", str(exc), "NO"])
                # ── Live write to joined CSV + Excel ─────────────────────────
                jw.writerow([idx, str(exc), "NO"] + row)
                joined_csv_file.flush()
                ws_joined.append([idx, str(exc), "NO"] + row)
                ws_clean.append(row)
                self._log(self.style.ERROR(f"  ERROR row {idx}: {exc}"))

        # ── Close CSV files and save Excel workbooks ─────────────────────────
        try:
            report_file.close()
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
            self._log(self.style.WARNING(f"  Error saving joined XLSX: {exc}"))
        try:
            wb_clean.save(str(clean_xlsx_path))
            self._log(f"  Saved clean XLSX: {clean_xlsx_path}")
        except Exception as exc:
            self._log(self.style.WARNING(f"  Error saving clean XLSX: {exc}"))
        self._log(f"  Joined/clean report files saved.")

        # ── Verbose summary (printed after normal loop end, or after Ctrl+C) ────
        self._log(f"\n{'='*60}")
        self._log(f"[import_legacy_habilitacion_urbana] Finished")
        self._log(f"  Processed: {processed}")
        self._log(f"  Rejected:  {rejected}")
        self._log(f"  Skipped:   {skipped}")
        if self.fecha_desde is not None:
            self._log(f"  Skipped by date: {skipped_by_date}")
        self._log(f"  Errors:    {errors}")
        self._log(f"")
        self._log(f"  RH rows parsed:             {rh_rows_parsed}")
        self._log(f"  RH slots candidates:         {rh_slots_candidates}")
        self._log(f"  RH slots skipped (no del):  {rh_slots_skipped_no_delegate}")
        self._log(f"  Comprobantes parsed:         {rh_comprobantes_parsed}")
        self._log(f"  Comprobantes invalid:        {rh_comprobantes_invalid}")
        self._log(f"")
        self._log(f"  Perfiles creados:            {rh_perfiles_creados}")
        self._log(f"  Perfiles reusados:          {rh_perfiles_reusados}")
        self._log(f"  Delegados creados:           {rh_delegados_creados}")
        self._log(f"  Delegados reusados:         {rh_delegados_reusados}")
        self._log(f"  Operaciones creadas:        {rh_operaciones_creadas}")
        self._log(f"  Operaciones reusadas:       {rh_operaciones_reusadas}")
        self._log(f"  Operaciones error:          {rh_operaciones_error}")
        self._log(f"")
        self._log(f"  LiquidacionDelegado creados:  {rh_ld_creados}")
        self._log(f"  LiquidacionDelegado reusados: {rh_ld_reusados}")
        self._log(f"  LiquidacionDelegado errores:  {rh_ld_error}")
        self._log(f"  LiquidacionDelegado sin liq:  {rh_ld_no_liquidacion}")
        self._log(f"  LiquidacionDelegado ambiguos: {rh_ld_ambiguo}")
        self._log(f"")
        self._log(f"  DetalleHonorario creados:     {rh_dh_creados}")
        self._log(f"  DetalleHonorario reusados:   {rh_dh_reusados}")
        self._log(f"  DetalleHonorario errores:    {rh_dh_error}")
        self._log(f"")
        self._log(f"  Comprobantes creados:        {rh_comp_creados}")
        self._log(f"  Comprobantes actualizados:   {rh_comp_actualizados}")
        self._log(f"  Comprobantes omitidos:       {rh_comp_omitidos}")
        self._log(f"  Comprobantes errores:       {rh_comp_errores}")
        self._log(f"  Reportes en {result_dir}:")
        self._log(f"    reporte_ingesta_legacy.csv")
        self._log(f"    reporte_rechazadas.csv + .xlsx")
        self._log(f"    filas_rechazadas_para_corregir.csv + .xlsx")
