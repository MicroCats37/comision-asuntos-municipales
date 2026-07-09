"""
Management command to build colegiados_reales.json from the CIP endpoint.

Uses CIPs from delegados_reales.json as input and fetches detailed
colegiado data from the CIP endpoint.

Usage:
    python manage.py build_colegiados_reales_json --settings=config.settings.development
    python manage.py build_colegiados_reales_json --dry-run --settings=config.settings.development
    python manage.py build_colegiados_reales_json --limit 5 --skip-errors --settings=config.settings.development

Input default: backend/modules/liquidaciones/seeds/delegados_reales.json
Output default: backend/modules/liquidaciones/seeds/colegiados_reales.json
Endpoint: http://172.16.93.83.9001/api/v1/colegiado/{cip}
"""

import json
import logging
import time
import unicodedata
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Build colegiados_reales.json by fetching CIP data from the endpoint"

    DEFAULT_ENDPOINT = "http://172.16.93.83:9001/api/v1/colegiado/{cip}"
    DEFAULT_DELEGADOS_SEED = (
        Path(settings.BASE_DIR) / 'modules' / 'liquidaciones' / 'seeds' / 'delegados_reales.json'
    )
    DEFAULT_OUTPUT = (
        Path(settings.BASE_DIR) / 'modules' / 'liquidaciones' / 'seeds' / 'colegiados_reales.json'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--delegados-seed-path',
            type=str,
            default=None,
            help='Ruta al archivo JSON seed de delegados',
        )
        parser.add_argument(
            '--output-path',
            type=str,
            default=None,
            help='Ruta de salida para colegiados_reales.json',
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
            '--force',
            action='store_true',
            help='Sobrescribir/actualizar entradas existentes en el output',
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            help='Continuar si hay errores en el fetch de un CIP',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo imprime conteo y CIPs a consultar sin llamar endpoint o escribir archivo',
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
        self.delegados_seed_path = (
            Path(options['delegados_seed_path'])
            if options['delegados_seed_path']
            else self.DEFAULT_DELEGADOS_SEED
        )
        self.output_path = (
            Path(options['output_path'])
            if options['output_path']
            else self.DEFAULT_OUTPUT
        )
        self.endpoint_url = options['endpoint_url'] or self.DEFAULT_ENDPOINT
        self.timeout = options['timeout']
        self.limit = options['limit']
        self.force = options['force']
        self.skip_errors = options['skip_errors']
        self.retries = options['retries']
        self.delay = options['delay']

        self._log(f"\n[build_colegiados_reales_json] Starting...")

        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE - No endpoint calls or file writes"))

        # Load existing output if present
        self.existing_data = self._load_existing_output()

        # Load delegados and collect unique CIPs
        cips_to_fetch = self._load_and_collect_cips()
        total_cips = len(cips_to_fetch)

        if self.limit and self.limit < total_cips:
            cips_to_fetch = cips_to_fetch[:self.limit]
            self._log(f"  Limited to {self.limit} CIPs (total: {total_cips})")

        if self.dry_run:
            self._log(f"\n  CIPs to fetch ({len(cips_to_fetch)}):")
            for cip in cips_to_fetch[:20]:
                self._log(f"    - {cip}")
            if len(cips_to_fetch) > 20:
                self._log(f"    ... and {len(cips_to_fetch) - 20} more")
            self._log(self.style.SUCCESS(f"\n[build_colegiados_reales_json] Dry-run complete"))
            return

        # Fetch and build
        self._fetch_and_write(cips_to_fetch)

        self._log(self.style.SUCCESS(
            f"\n[build_colegiados_reales_json] Completed successfully"
        ))

    def _log(self, msg):
        """Log message safely, handling encoding issues on Windows."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            safe_msg = msg.encode('ascii', 'replace').decode('ascii')
            self.stdout.write(safe_msg)

    def _load_existing_output(self):
        """Load existing output file if it exists."""
        if not self.output_path.exists():
            return {}

        try:
            content = self.output_path.read_text(encoding='utf-8')
            data = json.loads(content)
            colegiados = data.get('colegiados', [])
            return {item['cip']: item for item in colegiados}
        except (json.JSONDecodeError, KeyError, IOError) as e:
            self._log(self.style.WARNING(f"  Could not load existing output: {e}"))
            return {}

    def _load_and_collect_cips(self):
        """Load delegados JSON and collect unique normalized CIPs."""
        if not self.delegados_seed_path.exists():
            raise CommandError(f"Delegados seed file not found: {self.delegados_seed_path}")

        try:
            content = self.delegados_seed_path.read_text(encoding='utf-8')
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in seed file: {e}")

        cips = set()

        # Collect from delegados[]
        for dele in data.get('delegados', []):
            cip = self._normalize_cip(dele.get('cip', ''))
            if cip:
                cips.add(cip)

        # Also collect from asignaciones[] if present
        for asign in data.get('asignaciones', []):
            cip = self._normalize_cip(asign.get('cip', ''))
            if cip:
                cips.add(cip)

        self._log(f"  Loaded {len(data.get('delegados', []))} delegados, {len(data.get('asignaciones', []))} asignaciones")
        self._log(f"  Unique CIPs collected: {len(cips)}")

        if self.existing_data and not self.force:
            existing_count = len(self.existing_data)
            already_done = cips & set(self.existing_data.keys())
            self._log(f"  Already have data for {len(already_done)} CIPs (use --force to refresh)")

        return sorted(cips)

    def _normalize_cip(self, cip):
        """Normalize CIP to 6 digits with leading zeros."""
        if not cip:
            return None
        cip = str(cip).strip().replace('-', '').replace(' ', '')
        if not cip.isdigit():
            return None
        return cip.zfill(6)[:6]

    def _fetch_and_write(self, cips):
        """Fetch CIP data from endpoint and write to output file."""
        total = len(cips)
        skipped_existing = 0
        fetched_ok = 0
        failed = 0

        results = dict(self.existing_data)  # Start with existing data

        for idx, cip in enumerate(cips, 1):
            # Skip if already exists and not force
            if cip in results and not self.force:
                skipped_existing += 1
                self._log(f"  [{idx}/{total}] SKIP {cip} (already exists)")
                continue

            # Fetch from endpoint
            self.stdout.write(f"  [{idx}/{total}] FETCH {cip}...")
            data = self._fetch_colegiado(cip)

            if data is None:
                failed += 1
                self._log(self.style.WARNING(f" FAILED"))
                if not self.skip_errors:
                    self._log(self.style.ERROR(f"    Stopping due to error (use --skip-errors to continue)"))
                    break
                continue

            # Map to output shape
            mapped = self._map_colegiado_response(cip, data)
            if mapped:
                results[cip] = mapped
                fetched_ok += 1
                self._log(self.style.SUCCESS(f" OK"))
            else:
                failed += 1
                self._log(self.style.WARNING(f" FAILED (no data)"))
                if not self.skip_errors:
                    break

            # Delay between requests
            if self.delay > 0 and idx < total:
                time.sleep(self.delay)

        # Write output
        self._write_output(results)

        # Summary
        self._log(f"\n  Summary:")
        self._log(f"    Total CIPs: {total}")
        self._log(f"    Skipped (existing): {skipped_existing}")
        self._log(f"    Fetched OK: {fetched_ok}")
        self._log(f"    Failed: {failed}")

    def _fetch_colegiado(self, cip):
        """Fetch colegiado data from endpoint with retries."""
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
                    self._log(f" (attempt {attempt} failed: {e}, retrying...)")
                    time.sleep(0.5)
                else:
                    self._log(f" (error after {self.retries} attempts: {e})")
                    return None

        return None

    def _map_colegiado_response(self, cip, data):
        """Map endpoint response to colegiados_reales.json shape."""
        try:
            nombre1 = (data.get('nombre1') or '').strip()
            nombre2 = (data.get('nombre2') or '').strip()
            nombres = ' '.join(part for part in [nombre1, nombre2] if part).strip()

            capitulo_raw = data.get('capitulo') or {}
            capitulo_data = data.get('capitulo') or {}

            return {
                'cip': cip,
                'dni': (data.get('dni') or '').strip() or None,
                'nombres': nombres or None,
                'apellido_paterno': (data.get('paterno') or '').strip() or None,
                'apellido_materno': (data.get('materno') or '').strip() or None,
                'fecha_nacimiento': data.get('fechaNacimiento') or None,
                'genero': data.get('codGenero') or None,
                'correo_personal': data.get('correoPers') or None,
                'correo_institucional': data.get('correoInst') or None,
                'direccion': data.get('direccion') or None,
                'ubigeo': data.get('distritoId') or None,
                'codigo_especialidad': data.get('codEspecialidad') or None,
                'capitulo': {
                    'registro_id': data.get('codCapitulo') or capitulo_data.get('id') or None,
                    'abreviacion': capitulo_data.get('abreviatura') or None,
                    'nombre': capitulo_data.get('descripcion') or None,
                    'grupo_envio_intitucional': capitulo_data.get('grupoEnviosInst') or None,
                } if (data.get('codCapitulo') or capitulo_data.get('id')) else None,
            }
        except Exception as e:
            self._log(self.style.WARNING(f"    Error mapping response for CIP {cip}: {e}"))
            return None

    def _write_output(self, results):
        """Write results to output JSON file atomically."""
        colegiados = sorted(results.values(), key=lambda x: x['cip'])

        output_data = {
            'version': '1.0',
            'source': 'Endpoint CIP materializado desde build_colegiados_reales_json',
            'count': len(colegiados),
            'colegiados': colegiados,
        }

        # Write atomically: write to temp file first, then rename
        temp_path = self.output_path.with_suffix('.tmp')
        try:
            temp_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding='utf-8')
            if self.output_path.exists():
                self.output_path.unlink()
            temp_path.rename(self.output_path)
            self._log(f"  Written {len(colegiados)} records to {self.output_path}")
        except Exception as e:
            self._log(self.style.ERROR(f"  Error writing output file: {e}"))
            if temp_path.exists():
                temp_path.unlink()
            raise CommandError(f"Failed to write output: {e}")
