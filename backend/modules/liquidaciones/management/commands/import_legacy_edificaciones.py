"""
Management command to import legacy edificaciones data from an Excel .xlsx file.

Usage:
    python manage.py import_legacy_edificaciones --settings=config.settings.development
    python manage.py import_legacy_edificaciones --dry-run --settings=config.settings.development

Source file:
    C:\\Users\\Usuario\\Desktop\\Aplicaciones\\CIP\\CAM\\aplicacion\\data-old\\data.csv
    (actual format: Excel .xlsx with 6527 rows × 119 columns, header in row 1)

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
import io
import logging
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
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
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.orchestrators.liquidacion_legacy.liquidacion_edificaciones_legacy_orchestrator import (
    LiquidacionEdificacionesLegacyOrchestrator,
)
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
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
from modules.usuarios.domain.models.usuario import Usuario

logger = logging.getLogger(__name__)

# Default path to legacy data file
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "data-old" / "data.csv"

# openpyxl column indices — 0-indexed (list(row) from iter_rows(values_only=True))
# Header (row 1): ID=0 NRO=1 RUC=2 NOMBRE=3 PROYECTO=4 DPTOPRDI=5 DIRECCION=6
# VALOROBRA=7 PORCENTAJE=8 SUBTOTAL=9 IGV=10 TOTAL=11 FECHA=12 DNI=13
# RAZONSOCIAL=14 NROFACTURA=15 CODPAGO=16 NROEXPDTE=17 NROREV=18 ESPECIALIDAD=19
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
COL_TFONO = 60         # índice legacy para telefono
COL_TPERSONA = 61      # índice legacy para nombre de persona
COL_USUARIO = 32      # índice legacy para nombre de usuario (nombre de la persona que tramita)

# Max revisions constant (from liquidacion constants)
MAX_REVISIONES = 5


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


class Command(BaseCommand):
    help = "Import legacy edificaciones data from Excel .xlsx file via LiquidacionEdificacionesLegacyOrchestrator"

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
            help=f"Ruta al archivo Excel (default: {DEFAULT_DATA_PATH})",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Log a checkpoint every N rows (default: 100)",
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
        self.dry_run = bool(options["dry_run"])
        self.batch_size = int(options["batch_size"])
        self.reset = bool(options.get("reset", False))
        self.solo_reporte = bool(options.get("solo_report", False)) or bool(options.get("solo_reporte", False))
        self.rechazar_dif_alta = bool(options.get("rechazar_dif_alta", False))
        self.umbral_dif = Decimal(str(options.get("umbral_dif", 1.0)))

        data_path = Path(options["data_path"]) if options["data_path"] else DEFAULT_DATA_PATH
        if not data_path.exists():
            raise CommandError(f"Data file not found: {data_path}")

        self._log("\n[import_legacy_edificaciones] Starting...")
        self._log(f"  Source: {data_path}")
        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE — no database writes"))

        # Build injector and resolve orchestrator
        self._log("  Resolving orchestrator...")
        orchestrator = _build_orchestrator()
        self._log("  Orchestrator ready.")

        # Read Excel
        rows = self._read_excel(data_path)
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

        # Open CSV for report of problematic rows (what's wrong + whether it was uploaded)
        report_csv_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "reporte_ingesta_legacy.csv"
        report_file = report_csv_path.open("w", newline="", encoding="utf-8")
        report_writer = csv.writer(report_file)
        report_writer.writerow(["FILA", "EXPEDIENTE", "MOTIVO", "SUBIDO"])

        # Process
        processed = 0
        rejected = 0
        errors = 0
        total_todas = 0
        error_details: list[str] = []

        for idx, row in enumerate(rows, start=2):  # row 2 onward (row 1 is header)
            # No ESPECIALIDAD filter — process ALL rows
            especialidad_raw = row[COL_ESPECIALIDAD]
            if especialidad_raw and str(especialidad_raw).strip().upper() == "TODAS":
                total_todas += 1

            try:
                # ── Rechazo: NRO == 0 (filas anómalas, no se suben) ──────────
                nro_raw = row[1] if len(row) > 1 else None
                try:
                    nro_val = int(float(str(nro_raw).strip())) if nro_raw is not None and str(nro_raw).strip() != "" else None
                except (ValueError, TypeError):
                    nro_val = None
                if nro_val == 0:
                    report_writer.writerow([idx, "", "NRO == 0", "NO"])
                    rejected += 1
                    self._log(self.style.WARNING(f"  RECHAZADO row {idx}: NRO == 0"))
                    continue

                # ── Rechazo: DPTOPRDI vacío (distrito obligatorio) ──────────
                dptoprdri = row[COL_DPTOPRDI]
                if dptoprdri is None or str(dptoprdri).strip() == "":
                    report_writer.writerow([idx, "", "Distrito vacío (DPTOPRDI)", "NO"])
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
                        report_writer.writerow([
                            idx,
                            payload.liquidacion_general.expediente or "",
                            f"Diferencia alta subtotal: legacy={excel_subtotal}, recalc={recal_subtotal}, diff={diff} > {self.umbral_dif}",
                            "NO",
                        ])
                        rejected += 1
                        continue

                # Get usuario from USUARIO column (per-row)
                usuario_raw = row[COL_USUARIO] if len(row) > COL_USUARIO else None
                usuario = _get_or_create_usuario_from_usuario(usuario_raw)

                if not self.dry_run:
                    orchestrator.crear_legacy_proceso(
                        usuario_id=usuario.id,
                        payload=payload,
                    )

                processed += 1
                if anomalies:
                    for a in anomalies:
                        report_writer.writerow([idx, payload.liquidacion_general.expediente or "", a, "SI" if not self.dry_run else "DRY"])
                if processed % self.batch_size == 0:
                    self._log(f"  Checkpoint: {processed}/{total_rows} rows processed")
            except Exception as exc:  # noqa: BLE001
                errors += 1
                codpago = row[COL_CODPAGO] if len(row) > COL_CODPAGO else None
                msg = f"Row {idx} (CODPAGO={str(codpago)!r}): {exc}"
                error_details.append(msg)
                report_writer.writerow([idx, "", f"ERROR: {exc}", "NO"])
                self._log(self.style.ERROR(f"  ERROR row {idx}: {exc}"))

        report_file.close()

        # Summary report
        self._log(self.style.SUCCESS("\n=== REPORTE DE IMPORTACION LEGACY ==="))
        self._log(f"  Total filas 'TODAS': {total_todas}")
        self._log(f"  Procesadas (subidas): {processed}")
        self._log(f"  Rechazadas (NRO==0 o distrito vacío): {rejected}")
        self._log(f"  Errores: {errors}")
        self._log(f"  Reporte CSV: {report_csv_path}")

        if error_details:
            self._log(self.style.WARNING("\n  Error details (first 20):"))
            for detail in error_details[:20]:
                self._log(f"    {detail}")
            if len(error_details) > 20:
                self._log(f"    ... and {len(error_details) - 20} more errors")

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
                    True,
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

    def _read_excel(self, path: Path) -> list:
        """
        Read an Excel .xlsx file with openpyxl.

        The source file has a .csv extension but is actually an Excel .xlsx file.
        openpyxl rejects the extension, so we read as binary and load via BytesIO.

        Header is in row 1, data rows are 2..6527.
        Returns a list of rows (each row is a list of cell values, 1-indexed access via row[col]).
        """
        with path.open("rb") as f:
            data = f.read()
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        rows = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            rows.append(list(row))  # convert tuple to list for 0-indexed access
        wb.close()
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
        codpago_str = str(codpago).strip() if codpago is not None else ""
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

        # ── distrito (from DPTOPRDI column) ───────────────────────────────────
        dptoprdri = row[COL_DPTOPRDI]
        distrito_nombre = str(dptoprdri).split("/")[-1].strip() if dptoprdri else ""
        # Normalizar nombres históricos del Excel que no coinciden con la BD de ubigeo.
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

        # ── numero (secuencial de la liquidación específica) desde NRO ────────
        nro_raw = row[COL_NRO]
        numero = None
        if nro_raw is not None and str(nro_raw).strip() != "":
            try:
                numero = int(float(str(nro_raw).strip()))
            except (ValueError, TypeError):
                numero = None

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
