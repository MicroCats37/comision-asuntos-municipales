"""
Management command to build inspectores_reales.json from markdown and CIP endpoint.

Reads docs/doc-supervisores.md to extract structural metadata (CIP, numero_registro,
categoria, tipo_liquidacion, especialidad, vigencia) and fetches official identity
data from the CIP endpoint, producing a JSON seed for IO inspectors.

Usage:
    python manage.py build_inspectores_reales_json --settings=config.settings.development
    python manage.py build_inspectores_reales_json --dry-run --settings=config.settings.development
    python manage.py build_inspectores_reales_json --limit 5 --skip-errors --settings=config.settings.development

Input default: docs/doc-supervisores.md
Output default: backend/modules/liquidaciones/seeds/inspectores_reales.json
Endpoint: http://172.16.93.83:9001/api/v1/colegiado/{cip}

CRITICAL: This command does NOT write to the database. It only reads markdown and
fetches from the CIP endpoint to produce a JSON seed file.
"""

import json
import logging
import re
import time
import unicodedata
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Markdown parsing constants
# ---------------------------------------------------------------------------

# Vigencia hardcoded from the document header: "Periodo Agosto 2025 - Julio 2026"
VIGENCIA = "2026-07-31"

# Map section headers to tipo_liquidacion values
TIPO_LIQUIDACION_MAP = {
    "edificacion": "EDIFICACION",
    "edificaciones": "EDIFICACION",
    "habilitacion urbana": "HABILITACION_URBANA",
    "habilitación urbana": "HABILITACION_URBANA",
}

# Markdown table column indices for inspector rows (0-based)
# | N° | N° CIP | APELLIDOS Y NOMBRES | N° REGISTRO | CATEGORIA | NRO CELULAR | E-MAIL |
COL_IDX_NUMERO = 0
COL_IDX_CIP = 1
COL_IDX_NOMBRES = 2   # PII — to be explicitly ignored
COL_IDX_REGISTRO = 3
COL_IDX_CATEGORIA = 4
COL_IDX_CELULAR = 5   # PII — to be explicitly ignored
COL_IDX_EMAIL = 6     # PII — to be explicitly ignored


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_accents(text: str) -> str:
    """Remove diacritics/accents from text using Unicode normalization."""
    # Normalize to NFD (decomposed) then strip combining marks
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def normalize_tipo_liquidacion(header: str) -> str | None:
    """Derive tipo_liquidacion from a normalized header string.

    Handles accented characters by stripping diacritics before matching.
    Accepts both ASCII hyphen (-) and en-dash (–) as separators.
    """
    # Normalize: strip accents, lowercase, replace dashes with hyphen
    normalized = _strip_accents(header).lower()
    normalized = re.sub(r'[–—-]', '-', normalized)  # unify dashes

    for key, value in TIPO_LIQUIDACION_MAP.items():
        if key in normalized:
            return value
    return None


def normalize_especialidad(header: str) -> str | None:
    """Extract canonical especialidad name from a section header.

    Handles accented characters and various dash types.
    Examples:
        "Especialidad de Ingeniería Civil - Edificación" -> "Ingeniería Civil"
        "Especialidad de Ingeniería Sanitaria – Habilitación Urbana" -> "Ingeniería Sanitaria"
    """
    header = header.strip()
    # Remove leading "Especialidad de " or "Especialidad de "
    for prefix in ("Especialidad de ", "Especialidad de"):
        if header.startswith(prefix):
            header = header[len(prefix):]
    # Remove trailing " - Edificación" or " – Habilitación Urbana" etc.
    # Split on en-dash (–), em-dash (—), or hyphen (-) preceded by space(s)
    header = re.split(r'\s+[-–—]\s*', header)[0]
    return header.strip() or None


def parse_markdown_inspectores(markdown_text: str) -> list[dict]:
    """Parse inspector records from doc-supervisores.md.

    Returns a list of dicts with keys: cip, numero_registro, categoria,
    tipo_liquidacion, especialidad, vigencia.

    CRITICAL: Names, emails, and phone numbers are NEVER extracted — column
    indices 2, 5, and 6 are explicitly dropped.
    """
    records = []
    current_tipo_liquidacion: str | None = None
    current_especialidad: str | None = None

    for line in markdown_text.splitlines():
        stripped = line.strip()

        # Detect section headers (### ...)
        if stripped.startswith("###"):
            header_text = stripped.lstrip("#").strip()
            current_tipo_liquidacion = normalize_tipo_liquidacion(header_text)
            current_especialidad = normalize_especialidad(header_text)
            continue

        # Skip non-table rows
        if not stripped.startswith("|"):
            continue

        # Split columns
        cols = [c.strip() for c in stripped.split("|")]
        # cols[0] is empty (leading |), cols[-1] is empty (trailing |)
        if len(cols) < 7:
            continue

        # Skip header rows (check if N° CIP column is "N° CIP")
        if cols[COL_IDX_CIP + 1].startswith("N° CIP"):
            continue

        # Extract only structural metadata — explicitly drop PII columns
        cip_raw = cols[COL_IDX_CIP + 1].strip()
        numero_registro = cols[COL_IDX_REGISTRO + 1].strip()
        categoria_raw = cols[COL_IDX_CATEGORIA + 1].strip()

        # Validate CIP is numeric
        if not cip_raw.isdigit():
            continue

        cip = cip_raw.zfill(6)[:6]

        try:
            categoria = int(categoria_raw)
        except ValueError:
            categoria = None

        if current_tipo_liquidacion and current_especialidad:
            records.append({
                "cip": cip,
                "numero_registro": numero_registro,
                "categoria": categoria,
                "tipo_liquidacion": current_tipo_liquidacion,
                "especialidad": current_especialidad,
                "vigencia": VIGENCIA,
            })

    return records


def deduplicate_and_aggregate(records: list[dict]) -> dict[str, dict]:
    """Deduplicate records by CIP and aggregate multiple registros.

    Returns a dict keyed by CIP, where each value is a dict with:
        cip, registros: [record, ...]
    """
    aggregated: dict[str, dict] = {}

    for record in records:
        cip = record["cip"]
        if cip not in aggregated:
            aggregated[cip] = {
                "cip": cip,
                "registros": [],
            }
        # Append a copy so the original dict is not mutated
        aggregated[cip]["registros"].append({k: v for k, v in record.items() if k != "cip"})

    return aggregated


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Build inspectores_reales.json by merging markdown metadata with CIP endpoint data"

    DEFAULT_ENDPOINT = "http://172.16.93.83:9001/api/v1/colegiado/{cip}"
    DEFAULT_SOURCE = (
        Path(settings.BASE_DIR).parent / 'docs' / 'doc-supervisores.md'
    )
    DEFAULT_OUTPUT = (
        Path(settings.BASE_DIR) / 'modules' / 'liquidaciones' / 'seeds' / 'inspectores_reales.json'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default=None,
            help='Ruta al archivo markdown fuente (default: docs/doc-supervisores.md)',
        )
        parser.add_argument(
            '--output-path',
            type=str,
            default=None,
            help='Ruta de salida para inspectores_reales.json',
        )
        parser.add_argument(
            '--endpoint-url',
            type=str,
            default=None,
            help='URL del endpoint CIP (default: http://172.16.93.83:9001/api/v1/colegiado/{cip})',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=10,
            help='Timeout para requests al endpoint en segundos (default: 10)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limitar numero de CIPs a procesar (default: todos)',
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            help='Continuar si hay errores en el fetch de un CIP',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo imprime conteo sin llamar endpoint o escribir archivo',
        )
        parser.add_argument(
            '--retries',
            type=int,
            default=3,
            help='Numero de reintentos en caso de error de red (default: 3)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.1,
            help='Delay en segundos entre requests al endpoint (default: 0.1)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.source_path = (
            Path(options['source']) if options['source'] else self.DEFAULT_SOURCE
        )
        self.output_path = (
            Path(options['output_path']) if options['output_path'] else self.DEFAULT_OUTPUT
        )
        self.endpoint_url = options['endpoint_url'] or self.DEFAULT_ENDPOINT
        self.timeout = options['timeout']
        self.limit = options['limit']
        self.skip_errors = options['skip_errors']
        self.retries = options['retries']
        self.delay = options['delay']

        self._log(f"\n[build_inspectores_reales_json] Starting...")

        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE - No endpoint calls or file writes"))

        # Step 1: Parse markdown
        parsed_records = self._parse_markdown()
        if not parsed_records:
            raise CommandError("No inspector records found in markdown. Check source file.")

        # Step 2: Deduplicate and aggregate
        aggregated = deduplicate_and_aggregate(parsed_records)
        unique_cips = sorted(aggregated.keys())
        self._log(f"  Parsed {len(parsed_records)} records, {len(unique_cips)} unique CIPs")

        if self.limit and self.limit < len(unique_cips):
            unique_cips = unique_cips[:self.limit]
            self._log(f"  Limited to {self.limit} CIPs (total: {len(unique_cips)})")

        if self.dry_run:
            self._log(f"\n  CIPs to fetch ({len(unique_cips)}):")
            for cip in unique_cips[:20]:
                self._log(f"    - {cip} ({len(aggregated[cip]['registros'])} registros)")
            if len(unique_cips) > 20:
                self._log(f"    ... and {len(unique_cips) - 20} more")
            self._log(self.style.SUCCESS(f"\n[build_inspectores_reales_json] Dry-run complete"))
            return

        # Step 3: Fetch endpoint data and build final output
        self._fetch_and_write(unique_cips, aggregated)

        self._log(self.style.SUCCESS(
            f"\n[build_inspectores_reales_json] Completed successfully"
        ))

    def _log(self, msg):
        """Log message safely, handling encoding issues on Windows."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            safe_msg = msg.encode('ascii', 'replace').decode('ascii')
            self.stdout.write(safe_msg)

    def _parse_markdown(self) -> list[dict]:
        """Read and parse the markdown source file."""
        if not self.source_path.exists():
            raise CommandError(f"Source file not found: {self.source_path}")

        try:
            content = self.source_path.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            raise CommandError(f"Could not decode source file as UTF-8: {e}")

        records = parse_markdown_inspectores(content)
        self._log(f"  Parsed {len(records)} records from {self.source_path}")
        return records

    def _fetch_and_write(self, cips: list[str], aggregated: dict[str, dict]):
        """Fetch CIP identity data and write the final JSON.

        Raises CommandError if any CIP fails and --skip-errors is not set.
        Writes output only if all CIPs succeed or --skip-errors is set.
        """
        total = len(cips)
        fetched_ok = 0
        failed = 0

        inspectors = []

        for idx, cip in enumerate(cips, 1):
            self.stdout.write(f"  [{idx}/{total}] FETCH {cip}...")
            data = self._fetch_colegiado(cip)

            if data is None:
                failed += 1
                self._log(self.style.WARNING(f" FAILED"))
                if not self.skip_errors:
                    self._log(self.style.ERROR(f"    Aborting due to error (use --skip-errors to continue)"))
                    raise CommandError(
                        f"Fetch failed for CIP {cip} after {self.retries} retries. "
                        f"Aborting. Use --skip-errors to continue on failure."
                    )
                continue

            # Build inspector object with identidad from endpoint + registros from markdown
            identidad = self._map_identidad_response(cip, data)
            inspector = {
                "cip": cip,
                "identidad": identidad,
                "registros": aggregated[cip]["registros"],
            }
            inspectors.append(inspector)
            fetched_ok += 1
            self._log(self.style.SUCCESS(f" OK"))

            # Delay between requests
            if self.delay > 0 and idx < total:
                time.sleep(self.delay)

        # Write output only if we have results and no unhandled failures
        if inspectors:
            self._write_output(inspectors)

        # Summary
        self._log(f"\n  Summary:")
        self._log(f"    Total CIPs: {total}")
        self._log(f"    Fetched OK: {fetched_ok}")
        self._log(f"    Failed: {failed}")

    def _fetch_colegiado(self, cip: str) -> dict | None:
        """Fetch identity data for a CIP from the endpoint with retries."""
        url = self.endpoint_url.format(cip=cip)

        for attempt in range(1, self.retries + 1):
            try:
                response = requests.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    self._log(f" (404 Not Found for CIP {cip})")
                    return None
                else:
                    self._log(f" (status {response.status_code})")
            except requests.RequestException as e:
                if attempt < self.retries:
                    self._log(f" (attempt {attempt} failed: {e}, retrying in {self.delay}s...)")
                    time.sleep(self.delay)
                else:
                    self._log(f" (error after {self.retries} attempts: {e})")
                    return None

        return None

    def _map_identidad_response(self, cip: str, data: dict) -> dict:
        """Map endpoint response to the identidad object shape.

        Follows the same mapping pattern as build_colegiados_reales_json.
        Returns None-valued fields when data is missing.
        """
        nombre1 = (data.get('nombre1') or '').strip()
        nombre2 = (data.get('nombre2') or '').strip()
        nombres = ' '.join(part for part in [nombre1, nombre2] if part).strip()

        capitulo_raw = data.get('capitulo') or {}

        return {
            "nombres": nombres or None,
            "dni": (data.get('dni') or '').strip() or None,
            "apellido_paterno": (data.get('paterno') or '').strip() or None,
            "apellido_materno": (data.get('materno') or '').strip() or None,
            "correo_personal": data.get('correoPers') or None,
            "codigo_especialidad": data.get('codEspecialidad') or None,
            "capitulo": {
                "registro_id": data.get('codCapitulo') or capitulo_raw.get('id') or None,
                "abreviacion": capitulo_raw.get('abreviatura') or None,
                "nombre": capitulo_raw.get('descripcion') or None,
            } if (data.get('codCapitulo') or capitulo_raw.get('id')) else None,
        }

    def _write_output(self, inspectors: list[dict]):
        """Write the final JSON file atomically."""
        # Sort by CIP for deterministic output
        sorted_inspectors = sorted(inspectors, key=lambda x: x['cip'])

        output_data = sorted_inspectors  # Root is an array

        # Write atomically: write to temp file first, then rename
        temp_path = self.output_path.with_suffix('.tmp')
        try:
            temp_path.write_text(
                json.dumps(output_data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            if self.output_path.exists():
                self.output_path.unlink()
            temp_path.rename(self.output_path)
            self._log(f"  Written {len(sorted_inspectors)} inspector records to {self.output_path}")
        except Exception as e:
            self._log(self.style.ERROR(f"  Error writing output file: {e}"))
            if temp_path.exists():
                temp_path.unlink()
            raise CommandError(f"Failed to write output: {e}")