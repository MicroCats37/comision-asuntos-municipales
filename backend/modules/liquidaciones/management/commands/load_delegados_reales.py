"""
Management command to load real delegados data from seed JSON or markdown.

Usage:
    python manage.py load_delegados_reales --settings=config.settings.development
    python manage.py load_delegados_reales --dry-run --settings=config.settings.development
    python manage.py load_delegados_reales --skip-endpoint --settings=config.settings.development
    python manage.py load_delegados_reales --source markdown --settings=config.settings.development

Seed data sources (JSON mode):
  - backend/modules/liquidaciones/seeds/delegados_reales.json   (municipalidades/delegados/asignaciones)
  - backend/modules/liquidaciones/seeds/colegiados_reales.json  (PerfilIngeniero/Capitulo materializado)
  - Endpoint: http://172.16.93.83:9001/api/v1/colegiado/{cip}

Markdown mode:
  - docs/desarrollo/delegados-electrica-mecanica.md - Contains DELEGADOS TITULARES Y ALTERNOS DE INGENIERÍA ELÉCTRICA Y MECÁNICA ELÉCTRICA
"""

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import List, Tuple, Optional

import requests
import markdown
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError

from modules.entidades.models import Banco
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.delegado import Delegado, TipoDelegado, CategoriaDelegado, MunicipalidadDelegado, PeriodoDelegado
from modules.liquidaciones.domain.models.especialidades import Especialidad
from modules.liquidaciones.domain.constants import DelegadoStatus
from modules.usuarios.models import PerfilIngeniero
from modules.usuarios.domain.models.perfil_ingeniero import Capitulo


logger = logging.getLogger(__name__)


def normalize_specialty_name(name: str) -> str:
    """Remove accents/diacritics from a specialty name for canonical comparison.

    Uses NFD decomposition to strip combining diacritical marks (accents)
    so that 'Ingeniería Civil' and 'Ingenieria Civil' both normalize to
    'Ingenieria Civil' for deduplication purposes.
    """
    if not name:
        return name
    normalized = unicodedata.normalize('NFD', name)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')


# Canonical specialty names (with proper accents) — these are the authoritative names.
CANONICAL_SPECIALTY_NAMES = [
    'Ingeniería Civil',
    'Ingeniería Sanitaria',
    'Ingeniería Eléctrica y Mecánica Eléctrica',
]

# Mapping from unaccented/normalized variants to canonical names.
# Used to canonicalize seed data and avoid duplicates.
SPECIALTY_NORMALIZATION_MAP = {
    'ingenieria civil': 'Ingeniería Civil',
    'ingenieria sanitaria': 'Ingeniería Sanitaria',
    'ingenieria electrica y mecanica electrica': 'Ingeniería Eléctrica y Mecánica Eléctrica',
}


def get_canonical_specialty_name(raw_name: str) -> str:
    """Return the canonical accented specialty name for a raw name from seed data.

    Handles both accented and unaccented variants by normalizing and looking up
    in the canonical map. If no mapping exists, returns the original name unchanged.
    """
    if not raw_name:
        return raw_name
    # Strip category suffix if present: "Ingeniería Civil - Edificaciones" -> "Ingeniería Civil"
    base_name = raw_name.split(' - ')[0].strip()
    normalized = normalize_specialty_name(base_name).lower()
    return SPECIALTY_NORMALIZATION_MAP.get(normalized, base_name)

# Constants for markdown source
MARKDOWN_SPECIALTY = "Ingeniería Eléctrica y Mecánica Eléctrica - Edificaciones"
MARKDOWN_MUNICIPALIDAD_CODE_PREFIX = "ELE"


class Command(BaseCommand):
    help = "Cargar datos reales de delegados desde JSON seed"

    COLEGIADO_ENDPOINT = "http://172.16.93.83:9001/api/v1/colegiado/{cip}"

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['json', 'markdown'],
            default='json',
            help='Fuente de datos: json (default) o markdown',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validar datos seed y parsing sin escribir en la base de datos',
        )
        parser.add_argument(
            '--skip-endpoint',
            action='store_true',
            help='Omitir obtener detalles del Colegio desde el endpoint, usar solo datos seed',
        )
        parser.add_argument(
            '--seed-path',
            type=str,
            default=None,
            help='Ruta al archivo JSON seed de delegados',
        )
        parser.add_argument(
            '--colegiados-seed-path',
            type=str,
            default=None,
            help='Ruta al archivo JSON seed de colegiados (datos de PerfilIngeniero/Capitulo)',
        )
        parser.add_argument(
            '--markdown-path',
            type=str,
            default=None,
            help='Ruta al archivo markdown con delegados de Ingeniería Eléctrica',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.skip_endpoint = options['skip_endpoint']
        self.source = options['source']
        self.seed_path = (
            Path(options['seed_path'])
            if options['seed_path']
            else Path(settings.BASE_DIR) / 'modules' / 'liquidaciones' / 'seeds' / 'delegados_reales.json'
        )
        self.colegiados_seed_path = (
            Path(options['colegiados_seed_path'])
            if options['colegiados_seed_path']
            else Path(settings.BASE_DIR) / 'modules' / 'liquidaciones' / 'seeds' / 'colegiados_reales.json'
        )
        self.markdown_path = (
            Path(options['markdown_path'])
            if options['markdown_path']
            else Path(settings.BASE_DIR).parent / 'docs' / 'desarrollo' / 'delegados-electrica-mecanica.md'
        )

        self._log(f"\n[load_delegados_reales] Starting...")

        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE - No database writes will occur"))

        if self.source == 'markdown':
            self._handle_markdown_source()
        else:
            self._handle_json_source()

        self._log(self.style.SUCCESS(
            f"\n[load_delegados_reales] Completed successfully"
        ))

    def _handle_markdown_source(self):
        """Process delegates from markdown file."""
        self._log(f"  Source: markdown")
        self._log(f"  Markdown file: {self.markdown_path}")

        if not self.markdown_path.exists():
            raise CommandError(f"Markdown file not found: {self.markdown_path}")

        # Ensure the specialty exists
        self._ensure_markdown_especialidad()

        # Parse markdown and get rows
        rows = self._parse_markdown_table()
        self._log(f"  Parsed {len(rows)} rows from markdown")

        # Process each row
        muni_count = 0
        dele_count = 0
        asign_count = 0

        for row_num, row_data in enumerate(rows, start=1):
            m_result = self._process_markdown_row(row_data)
            muni_count += m_result['municipalidades']
            dele_count += m_result['delegados']
            asign_count += m_result['asignaciones']

        self._log(self.style.SUCCESS(
            f"\n  Completed: {muni_count} municipalidades, {dele_count} delegados, {asign_count} asignaciones processed"
        ))

    def _handle_json_source(self):
        """Process delegates from JSON seed file (original behavior)."""
        self._log(f"  Source: json")

        # Load colegiados seed into memory by CIP
        self.colegiados_seed_data = self._load_colegiados_seed()

        # Load seed data
        seed_data = self._load_seed()
        if not seed_data:
            raise CommandError("Failed to load seed data")

        # Ensure required specialties exist
        self._ensure_especialidades()

        # Process municipalities
        muni_count = self._process_municipalidades(seed_data.get('municipalidades', []))

        # Process delegates
        dele_count = self._process_delegados(seed_data.get('delegados', []))

        # Process municipality-delegate assignments
        asign_count = self._process_asignaciones(seed_data.get('asignaciones', []))

        self._log(self.style.SUCCESS(
            f"\n  Completed: {muni_count} municipalidades, {dele_count} delegados, {asign_count} asignaciones processed"
        ))

    def _log(self, msg):
        """Registra mensaje de forma segura, manejando problemas de codificación en Windows."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            # Respaldo para problemas de codificación en consola Windows
            safe_msg = msg.encode('ascii', 'replace').decode('ascii')
            self.stdout.write(safe_msg)

    def _load_seed(self):
        """Cargar archivo JSON seed."""
        if not self.seed_path.exists():
            raise CommandError(f"Seed file not found: {self.seed_path}")

        try:
            content = self.seed_path.read_text(encoding='utf-8')
            data = json.loads(content)
            self._log(f"  Loaded seed: version={data.get('version')}, periodo={data.get('periodo')}")
            return data
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in seed file: {e}")

    def _load_colegiados_seed(self):
        """Cargar archivo JSON seed de colegiados en memoria, indexado por CIP."""
        if not self.colegiados_seed_path.exists():
            self._log(self.style.WARNING(
                f"  Colegiados seed file not found: {self.colegiados_seed_path} - will use endpoint or fallback"
            ))
            return {}

        try:
            content = self.colegiados_seed_path.read_text(encoding='utf-8')
            data = json.loads(content)
            colegiados = data.get('colegiados', [])
            by_cip = {item['cip']: item for item in colegiados}
            self._log(f"  Loaded colegiados seed: {len(by_cip)} records")
            return by_cip
        except json.JSONDecodeError as e:
            self._log(self.style.WARNING(
                f"  Invalid JSON in colegiados seed file: {e} - will use endpoint or fallback"
            ))
            return {}

    def _ensure_especialidades(self):
        """Asegurar que las especialidades requeridas existan en la base de datos.

        Uses CANONICAL_SPECIALTY_NAMES (properly accented) as the authoritative names.
        If unaccented duplicates already exist in DB, they are NOT deleted here —
        run cleanup_especialidad_duplicates to consolidate them.
        """
        for spec_name in CANONICAL_SPECIALTY_NAMES:
            if self.dry_run:
                self._log(f"    [DRY-RUN] Would create/find especialidad: {spec_name}")
            else:
                spec, created = Especialidad.objects.get_or_create(
                    nombre=spec_name,
                    defaults={}
                )
                if created:
                    self._log(self.style.SUCCESS(f"    Created especialidad: {spec_name}"))
                else:
                    self._log(f"    Found existing especialidad: {spec_name}")

    def _normalize_cip(self, cip):
        """Normaliza CIP a 6 dígitos con ceros iniciales."""
        if not cip:
            return None
        cip = str(cip).strip().replace('-', '').replace(' ', '')
        if not cip.isdigit():
            return None
        return cip.zfill(6)[:6]

    def _get_or_fetch_colegiado(self, cip):
        """Obtiene detalles del colegiado desde el endpoint o retorna None."""
        if self.skip_endpoint:
            return None

        normalized_cip = self._normalize_cip(cip)
        if not normalized_cip:
            return None

        url = self.COLEGIADO_ENDPOINT.format(cip=normalized_cip)
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self._log(f"    Fetched endpoint data for CIP {normalized_cip}")
                return data
            else:
                self._log(self.style.WARNING(
                    f"    Endpoint returned {response.status_code} for CIP {normalized_cip}"
                ))
                return None
        except requests.RequestException as e:
            self._log(self.style.WARNING(
                f"    Endpoint unavailable for CIP {normalized_cip}: {e}"
            ))
            return None

    def _process_municipalidades(self, municipalidades):
        """Crear/actualizar municipalidades desde datos seed."""
        count = 0
        seen_codes = set()  # Seguimiento de códigos en esta ejecución para detectar duplicados
        duplicate_codes = set()

        for muni_data in municipalidades:
            nombre = muni_data.get('nombre', '').strip()
            if not nombre:
                continue

            # Use pre-generated code from seed data
            code = muni_data.get('codigo', '').strip()
            if not code:
                self._log(self.style.ERROR(
                    f"    ERROR: Municipality '{nombre}' is missing a 'codigo' field in seed data"
                ))
                continue

            # Check for duplicate codes within this seed data
            if code in seen_codes:
                duplicate_codes.add(code)
                self._log(self.style.ERROR(
                    f"    DUPLICATE CODE: '{code}' used for both '{nombre}' and previously seen municipality"
                ))
            seen_codes.add(code)

            if self.dry_run:
                self._log(f"    [DRY-RUN] Would create/update municipalidad: {nombre} (code={code})")
            else:
                muni, created = Municipalidad.objects.update_or_create(
                    codigo=code,
                    defaults={
                        'nombre': nombre,
                        'provincia': muni_data.get('provincia'),
                        'distrito': muni_data.get('distrito'),
                        'activo': True,
                    }
                )
                action = "created" if created else "updated"
                self._log(f"    {action} municipalidad: {nombre}")

            count += 1

        # Report any duplicates found
        if duplicate_codes:
            dup_list = ', '.join(sorted(duplicate_codes))
            self._log(self.style.ERROR(
                f"\n  ERROR: Found {len(duplicate_codes)} duplicate municipality codes in seed data: {dup_list}"
            ))
            raise CommandError(f"Duplicate municipality codes detected: {dup_list}")

        return count

    def _process_asignaciones(self, asignaciones):
        """Crear/actualizar asignaciones MunicipalidadDelegado desde datos seed."""
        count = 0
        for asignacion in asignaciones:
            cip = self._normalize_cip(asignacion.get('cip', ''))
            muni_code = asignacion.get('municipalidad_codigo')
            if not cip or not muni_code:
                continue

            if self.dry_run:
                self._log(
                    f"    [DRY-RUN] Would assign delegado CIP={cip} to municipalidad={muni_code}"
                )
                count += 1
                continue

            try:
                delegado = Delegado.objects.select_related('perfil_ingeniero').get(
                    perfil_ingeniero__cip=cip
                )
                municipalidad = Municipalidad.objects.get(codigo=muni_code)
                tipo = asignacion.get('tipo', 'titular')
                tipo_delegado = TipoDelegado.TITULAR if tipo == 'titular' else TipoDelegado.ALTERNO

                # Extraer categoria de la especialidad: "Ingeniería Civil - Edificaciones" -> categoria="Edificaciones"
                especialidad_raw = asignacion.get('especialidad', '')
                categoria = self._extract_categoria_from_especialidad(especialidad_raw)
                if categoria:
                    categoria_delegado = categoria
                else:
                    categoria_delegado = None

                _, created = MunicipalidadDelegado.objects.update_or_create(
                    delegado=delegado,
                    municipalidad=municipalidad,
                    defaults={
                        'activo': True,
                        'tipo': tipo_delegado,
                        'categoria': categoria_delegado,
                    },
                )
                action = 'created' if created else 'updated'
                self._log(
                    f"    {action} asignación: {delegado.perfil_ingeniero.cip} @ {municipalidad.nombre} (categoria={categoria_delegado})"
                )
                count += 1
            except Delegado.DoesNotExist:
                self._log(self.style.WARNING(f"    Delegado not found for CIP {cip}, skipping assignment"))
            except Exception as e:
                self._log(self.style.WARNING(f"    Error assigning CIP {cip} to {muni_code}: {e}, skipping"))

        return count

    def _extract_categoria_from_especialidad(self, especialidad_raw: str) -> str | None:
        """Extrae la categoría de una especialidad cruda.

        Ejemplos:
            'Ingeniería Civil - Edificaciones' -> 'Edificaciones'
            'Ingeniería Civil - Habilitaciones Urbanas' -> 'Habilitaciones Urbanas'
            'Ingeniería Eléctrica y Mecánica Eléctrica - Edificaciones' -> 'Edificaciones'
        """
        if not especialidad_raw:
            return None

        # Split por " - " y tomar la última parte como categoria
        parts = especialidad_raw.split(' - ')
        if len(parts) >= 2:
            categoria = parts[-1].strip()
            # Validar que sea una categoria conocida
            if categoria == CategoriaDelegado.EDIFICACIONES:
                return CategoriaDelegado.EDIFICACIONES
            elif categoria == CategoriaDelegado.HABILITACIONES_URBANAS:
                return CategoriaDelegado.HABILITACIONES_URBANAS
        return None

    def _extract_clean_especialidad_nombre(self, especialidad_raw: str) -> str:
        """Extrae el nombre limpio de la especialidad y lo canoniza al nombre accented.

        Uses get_canonical_specialty_name to normalize both the category suffix
        removal AND accent/diacritic canonicalization (so 'Ingenieria Civil - Edificaciones'
        maps to 'Ingeniería Civil').

        Ejemplos:
            'Ingeniería Civil - Edificaciones' -> 'Ingeniería Civil'
            'Ingeniería Civil - Habilitaciones Urbanas' -> 'Ingeniería Civil'
            'Ingeniería Eléctrica y Mecánica Eléctrica - Edificaciones' -> 'Ingeniería Eléctrica y Mecánica Eléctrica'
            'Ingenieria Civil' -> 'Ingeniería Civil' (unaccented variant canonized)
            'Ingeniería Civil' -> 'Ingeniería Civil' (sin cambios si no tiene sufijo)
        """
        if not especialidad_raw:
            return 'Ingeniería Civil'  # Default

        # Split por " - " y tomar la primera parte como nombre limpio
        parts = especialidad_raw.split(' - ')
        base_name = parts[0].strip() if parts else especialidad_raw.strip()
        # Canonicalize to accented form
        return get_canonical_specialty_name(base_name)

    def _process_delegados(self, delegados):
        """Crear/actualizar delegados desde datos seed."""
        count = 0
        endpoint_data_cache = {}

        for dele_data in delegados:
            cip = self._normalize_cip(dele_data.get('cip', ''))
            if not cip:
                self._log(self.style.WARNING(
                    f"    Skipping delegado with invalid CIP: {dele_data.get('cip')}"
                ))
                continue

            nombre_completo = dele_data.get('nombre_completo', '')
            # Extraer nombre limpio de la especialidad (sin " - Edificaciones" o " - Habilitaciones Urbanas")
            especialidad_raw = dele_data.get('especialidad', 'Ingeniería Civil')
            especialidad_nombre = self._extract_clean_especialidad_nombre(especialidad_raw)
            tipo = dele_data.get('tipo', 'titular')

            # Fetch from endpoint if not skipped
            if not self.skip_endpoint and cip not in endpoint_data_cache:
                endpoint_data_cache[cip] = self._get_or_fetch_colegiado(cip)

            endpoint_data = endpoint_data_cache.get(cip)

            # Get or create PerfilIngeniero
            perfil = self._get_or_create_perfil(
                cip=cip,
                dele_data=dele_data,
                endpoint_data=endpoint_data,
            )

            if not perfil and not self.dry_run:
                self._log(self.style.ERROR(
                    f"    Failed to get/create PerfilIngeniero for CIP {cip}"
                ))
                continue

            # Get especialidad
            especialidad = None
            try:
                especialidad = Especialidad.objects.get(nombre=especialidad_nombre)
            except Especialidad.DoesNotExist:
                if self.dry_run:
                    self._log(f"    [DRY-RUN] Especialidad '{especialidad_nombre}' not found in DB, skipping DB validation")
                else:
                    self._log(self.style.WARNING(
                        f"    Especialidad not found: {especialidad_nombre}, skipping delegado {cip}"
                    ))
                    continue

            # NOTE: tipo is now set on MunicipalidadDelegado, not on Delegado itself
            tipo_delegado = TipoDelegado.TITULAR if tipo == 'titular' else TipoDelegado.ALTERNO

            if self.dry_run:
                self._log(f"    [DRY-RUN] Would create/update delegado: {nombre_completo} (CIP={cip})")
            else:
                delegado, created = Delegado.objects.update_or_create(
                    perfil_ingeniero=perfil,
                    defaults={
                        'especialidad': especialidad,
                        'banco': None,  # Banco remains null
                        'status': DelegadoStatus.ACTIVO,
                    }
                )
                action = "created" if created else "updated"
                self._log(f"    {action} delegado: {nombre_completo}")

                if created:
                    PeriodoDelegado.objects.get_or_create(
                        delegado=delegado,
                        periodo_inicio=timezone.now().date(),
                        defaults={'periodo_fin': None},
                    )

            count += 1

        return count

    def _get_or_create_perfil(self, cip, dele_data, endpoint_data):
        """Obtener o crear PerfilIngeniero.

        Prioridad:
        a) Usar colegiados_seed_data si está disponible (seed local - preferido)
        b) Obtener desde endpoint si no se omitió
        c) Recurrir a datos seed mínimos de delegados_reales.json
        """
        # Check if we have colegiados seed data for this CIP
        colegiados_seed_item = self.colegiados_seed_data.get(cip)

        # Try to find existing
        try:
            perfil = PerfilIngeniero.objects.get(cip=cip)
            # Update from colegiados seed, endpoint, or skip if dry-run
            if not self.dry_run:
                if colegiados_seed_item:
                    self._update_perfil_from_seed(perfil, colegiados_seed_item)
                elif endpoint_data:
                    self._update_perfil_from_endpoint(perfil, endpoint_data)
            return perfil
        except PerfilIngeniero.DoesNotExist:
            pass

        if self.dry_run:
            if colegiados_seed_item:
                self._log(f"    [DRY-RUN] Would create PerfilIngeniero from colegiados_seed: CIP={cip}")
            elif endpoint_data:
                self._log(f"    [DRY-RUN] Would create PerfilIngeniero from endpoint: CIP={cip}")
            else:
                self._log(f"    [DRY-RUN] Would create PerfilIngeniero from seed: CIP={cip}")
            return None

        # Create from colegiados seed (preferred), endpoint, or fallback seed
        if colegiados_seed_item:
            return self._create_perfil_from_colegiados_seed(cip, colegiados_seed_item)
        elif endpoint_data:
            return self._create_perfil_from_endpoint(cip, endpoint_data)
        else:
            return self._create_perfil_from_seed(cip, dele_data)

    def _create_perfil_from_seed(self, cip, dele_data):
        """Crear o obtener PerfilIngeniero desde datos seed (fallback cuando no hay endpoint ni colegiados_seed).

        Uses transaction-safe patterns to handle concurrent seed runs.
        When dni is provided, uses get_or_create by dni (preferred).
        When dni is absent, uses get_or_create by cip to handle the case where
        the seed data only has CIP (como delegados_reales.json sin dni).

        When individual name fields are missing but nombre_completo is available,
        parses it into components using the pattern: "APELLIDO_PATERNO APELLIDO_MATERNO NOMBRES".
        If no name data at all, generates a deterministic placeholder from CIP.
        """
        dni = dele_data.get('dni')

        # If no DNI provided, use a placeholder. The dni field in PerfilIngeniero
        # is required (no blank=True, null=True) and unique, so we must provide a value.
        # "00000000" is the conventional placeholder when real DNI is unknown.
        if not dni:
            dni = '00000000'
        nombre = dele_data.get('nombre', '')
        paterno = dele_data.get('paterno', '')
        materno = dele_data.get('materno', '')

        # If name fields are empty but nombre_completo is available, parse it
        if not (nombre or paterno or materno):
            nombre_completo = dele_data.get('nombre_completo', '')
            if nombre_completo:
                parsed = self._parse_delegate_name(nombre_completo)
                nombre = parsed.get('nombres', '')
                paterno = parsed.get('apellido_paterno', '')
                materno = parsed.get('apellido_materno', '')
            else:
                # No name data at all — generate deterministic placeholder from CIP
                # This ensures the model validation passes (required fields)
                paterno = f'CIP{cip}'
                materno = 'INGRESADO'
                nombre = 'DELEGADO'

        # Validate we have non-empty values for required fields
        if not paterno:
            paterno = f'CIP{cip}'
        if not materno:
            materno = 'PENDIENTE'
        if not nombre:
            nombre = 'PENDIENTE'

        defaults = {
            'nombres': nombre,
            'apellido_paterno': paterno,
            'apellido_materno': materno,
        }

        try:
            if dni:
                # Use DNI as primary lookup (preferred — DNI is unique and stable)
                perfil, created = PerfilIngeniero.objects.get_or_create(
                    dni=dni,
                    defaults={**defaults, 'cip': cip},
                )
            else:
                # No valid DNI in seed data (e.g. delegados_reales.json fallback).
                # Use CIP as lookup - first check if exists, then create if not.
                # This avoids get_or_create's IntegrityError on concurrent inserts.
                try:
                    perfil = PerfilIngeniero.objects.get(cip=cip)
                    created = False
                except PerfilIngeniero.DoesNotExist:
                    try:
                        # Don't include dni in defaults when empty — empty string violates unique
                        perfil = PerfilIngeniero.objects.create(cip=cip, **defaults)
                        created = True
                    except IntegrityError:
                        # Concurrent creation — fetch the winner
                        perfil = PerfilIngeniero.objects.filter(cip=cip).first()
                        created = False
                        if not perfil:
                            self._log(self.style.ERROR(f"    IntegrityError recovery failed for CIP {cip}"))
                            return None
            if created:
                self._log(f"    Created PerfilIngeniero from seed: {dele_data.get('nombre_completo')}")
            else:
                # Profile exists — update CIP (if looked up by DNI) and name fields if different
                updated = False
                if dni and perfil.cip != cip:
                    perfil.cip = cip
                    updated = True
                for field, value in defaults.items():
                    if getattr(perfil, field) != value:
                        setattr(perfil, field, value)
                        updated = True
                if updated:
                    perfil.save()
                    self._log(f"    Updated PerfilIngeniero by {('DNI' if dni else 'CIP')} from seed: {perfil.nombre_completo}")
            return perfil
        except IntegrityError:
            # Rare race: unique constraint conflict during concurrent seed runs.
            # Fall back to CIP lookup — the most recently created record wins.
            existing = PerfilIngeniero.objects.filter(cip=cip).first()
            if existing:
                updated = False
                for field, value in defaults.items():
                    if getattr(existing, field) != value:
                        setattr(existing, field, value)
                        updated = True
                if updated:
                    existing.save()
                    self._log(f"    Updated PerfilIngeniero by CIP from seed (race recovery): {existing.nombre_completo}")
                return existing
            self._log(self.style.ERROR(f"    Could not resolve PerfilIngeniero for CIP {cip} / DNI {dni}"))
            return None
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating PerfilIngeniero: {e}"))
            return None

    def _create_perfil_from_colegiados_seed(self, cip, colegiados_seed_item):
        """Crear PerfilIngeniero desde datos seed materializados de colegiados."""
        try:
            capitulo = self._get_or_create_capitulo_from_seed(colegiados_seed_item.get('capitulo'))
            defaults = {
                'dni': colegiados_seed_item.get('dni') or '',
                'nombres': colegiados_seed_item.get('nombres') or '',
                'apellido_paterno': colegiados_seed_item.get('apellido_paterno') or '',
                'apellido_materno': colegiados_seed_item.get('apellido_materno') or '',
                'fecha_nacimiento': colegiados_seed_item.get('fecha_nacimiento') or None,
                'genero': colegiados_seed_item.get('genero') or None,
                'correo_personal': colegiados_seed_item.get('correo_personal') or None,
                'correo_institucional': colegiados_seed_item.get('correo_institucional') or None,
                'direccion': colegiados_seed_item.get('direccion') or None,
                'ubigeo': colegiados_seed_item.get('ubigeo') or None,
                'codigo_especialidad': colegiados_seed_item.get('codigo_especialidad') or None,
                'capitulo': capitulo,
            }
            perfil = PerfilIngeniero.objects.create(cip=cip, **defaults)
            self._log(f"    Created PerfilIngeniero from colegiados_seed: {perfil.nombre_completo}")
            return perfil
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating PerfilIngeniero from colegiados_seed for CIP {cip}: {e}"))
            return None

    def _update_perfil_from_seed(self, perfil, colegiados_seed_item):
        """Actualizar PerfilIngeniero existente desde datos seed de colegiados."""
        try:
            capitulo = self._get_or_create_capitulo_from_seed(colegiados_seed_item.get('capitulo'))
            fields_to_update = [
                'dni', 'nombres', 'apellido_paterno', 'apellido_materno',
                'fecha_nacimiento', 'genero', 'correo_personal', 'correo_institucional',
                'direccion', 'ubigeo', 'codigo_especialidad', 'capitulo',
            ]
            for field in fields_to_update:
                if field == 'capitulo':
                    setattr(perfil, field, capitulo)
                else:
                    value = colegiados_seed_item.get(field)
                    if value is not None:
                        setattr(perfil, field, value)
            perfil.save()
            self._log(f"    Updated PerfilIngeniero from colegiados_seed: {perfil.nombre_completo}")
        except Exception as e:
            self._log(self.style.WARNING(f"    Error updating PerfilIngeniero from seed: {e}"))

    def _get_or_create_capitulo_from_seed(self, capitulo_data):
        """Obtener o crear Capitulo desde datos seed."""
        if not capitulo_data:
            return None

        registro_id = capitulo_data.get('registro_id')
        abreviacion = capitulo_data.get('abreviacion')
        if not registro_id:
            return None

        capitulo = Capitulo.objects.filter(registro_id=registro_id).first()
        if not capitulo and abreviacion:
            capitulo = Capitulo.objects.filter(abreviacion=abreviacion).first()

        if capitulo:
            capitulo.nombre = capitulo_data.get('nombre') or capitulo.nombre
            capitulo.grupo_envio_intitucional = (
                capitulo_data.get('grupo_envio_intitucional') or capitulo.grupo_envio_intitucional
            )
            capitulo.save()
            return capitulo

        capitulo, _ = Capitulo.objects.update_or_create(
            registro_id=registro_id,
            defaults={
                'abreviacion': abreviacion or f'CAP{registro_id}',
                'nombre': capitulo_data.get('nombre') or f'Capítulo {registro_id}',
                'grupo_envio_intitucional': capitulo_data.get('grupo_envio_intitucional') or None,
            },
        )
        return capitulo

    def _create_perfil_from_endpoint(self, cip, endpoint_data):
        """Crear o reutilizar PerfilIngeniero desde datos del endpoint."""
        try:
            defaults = self._perfil_defaults_from_endpoint(endpoint_data)
            dni = defaults.get('dni')
            perfil = PerfilIngeniero.objects.filter(dni=dni).first() if dni else None

            if perfil:
                perfil.cip = cip
                for field, value in defaults.items():
                    setattr(perfil, field, value)
                perfil.save()
                self._log(f"    Updated PerfilIngeniero by DNI from endpoint: {perfil.nombre_completo}")
            else:
                perfil = PerfilIngeniero.objects.create(cip=cip, **defaults)
                self._log(f"    Created PerfilIngeniero from endpoint: {perfil.nombre_completo}")
            return perfil
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating PerfilIngeniero from endpoint for CIP {cip}: {e}"))
            return None

    def _update_perfil_from_endpoint(self, perfil, endpoint_data):
        """Actualizar PerfilIngeniero existente con datos del endpoint."""
        try:
            defaults = self._perfil_defaults_from_endpoint(endpoint_data)
            for field, value in defaults.items():
                setattr(perfil, field, value)
            perfil.save()
            self._log(f"    Updated PerfilIngeniero from endpoint: {perfil.nombre_completo}")
        except Exception as e:
            self._log(self.style.WARNING(f"    Error updating PerfilIngeniero: {e}"))

    def _perfil_defaults_from_endpoint(self, endpoint_data):
        """Mapear payload del endpoint CIP a campos de PerfilIngeniero."""
        nombre1 = (endpoint_data.get('nombre1') or '').strip()
        nombre2 = (endpoint_data.get('nombre2') or '').strip()
        nombres = ' '.join(part for part in [nombre1, nombre2] if part).strip()
        capitulo = self._get_or_create_capitulo_from_endpoint(endpoint_data)

        # Determinar habilitación CIP
        condicion = endpoint_data.get('condicion', '')
        habilitado_cip = condicion == '1'

        from django.utils import timezone
        return {
            'dni': (endpoint_data.get('dni') or '').strip(),
            'nombres': nombres,
            'apellido_paterno': (endpoint_data.get('paterno') or '').strip(),
            'apellido_materno': (endpoint_data.get('materno') or '').strip(),
            'fecha_nacimiento': endpoint_data.get('fechaNacimiento') or None,
            'genero': endpoint_data.get('codGenero') or None,
            'correo_personal': endpoint_data.get('correoPers') or None,
            'correo_institucional': endpoint_data.get('correoInst') or None,
            'direccion': endpoint_data.get('direccion') or None,
            'ubigeo': endpoint_data.get('distritoId') or None,
            'codigo_especialidad': endpoint_data.get('codEspecialidad') or None,
            'capitulo': capitulo,
            # Campos de habilitación CIP
            'habilitado_cip': habilitado_cip,
            'condicion_cip': condicion,
            'fecha_validacion_cip': timezone.now(),
            'ultimo_periodo_pagado_cip': endpoint_data.get('ultimoPeriodoPagado') or None,
        }

    def _get_or_create_capitulo_from_endpoint(self, endpoint_data):
        capitulo_data = endpoint_data.get('capitulo') or {}
        registro_id = endpoint_data.get('codCapitulo') or capitulo_data.get('id')
        abreviacion = capitulo_data.get('abreviatura') or registro_id
        if not registro_id:
            return None

        capitulo = Capitulo.objects.filter(registro_id=registro_id).first()
        if not capitulo and abreviacion:
            capitulo = Capitulo.objects.filter(abreviacion=abreviacion).first()

        if capitulo:
            capitulo.nombre = capitulo_data.get('descripcion') or capitulo.nombre
            capitulo.grupo_envio_intitucional = (
                capitulo_data.get('grupoEnviosInst') or capitulo.grupo_envio_intitucional
            )
            capitulo.save()
            return capitulo

        capitulo, _ = Capitulo.objects.update_or_create(
            registro_id=registro_id,
            defaults={
                'abreviacion': abreviacion,
                'nombre': capitulo_data.get('descripcion') or f'Capítulo {registro_id}',
                'grupo_envio_intitucional': capitulo_data.get('grupoEnviosInst') or None,
            },
        )
        return capitulo

    # ── Markdown Source Methods ──────────────────────────────────────────────────

    def _ensure_markdown_especialidad(self):
        """Ensure the Electrical Engineering specialty exists."""
        if self.dry_run:
            self._log(f"    [DRY-RUN] Would create/find especialidad: {MARKDOWN_SPECIALTY}")
            return

        spec, created = Especialidad.objects.get_or_create(
            nombre=MARKDOWN_SPECIALTY,
            defaults={}
        )
        if created:
            self._log(self.style.SUCCESS(f"    Created especialidad: {MARKDOWN_SPECIALTY}"))
        else:
            self._log(f"    Found existing especialidad: {MARKDOWN_SPECIALTY}")

    def _parse_markdown_table(self) -> List[dict]:
        """Parse the markdown file and extract table rows for Electrical Engineering delegates."""
        content = self.markdown_path.read_text(encoding='utf-8')

        # Convert markdown to HTML and parse
        html = markdown.markdown(content, extensions=['tables'])

        # Find the table containing "DELEGADOS TITULARES Y ALTERNOS DE INGENIERÍA ELÉCTRICA"
        rows = []
        in_target_table = False

        # Split by table tags to find our table
        table_pattern = re.compile(r'<table>(.*?)</table>', re.DOTALL | re.IGNORECASE)
        for table_match in table_pattern.finditer(html):
            table_html = table_match.group(0)
            # Check if this is the target table by looking for the specialty header
            if MARKDOWN_SPECIALTY.upper() in table_html.upper() or 'DELEGADOS TITULARES Y ALTERNOS' in table_html.upper():
                in_target_table = True
                rows = self._parse_html_table(table_html)
                break

        if not rows:
            # Fallback: try to parse any table with CIP numbers
            self._log(self.style.WARNING("  Could not find target table, attempting to parse first table with CIP data"))
            for table_match in table_pattern.finditer(html):
                potential_rows = self._parse_html_table(table_match.group(0))
                if potential_rows and any('cip' in str(r).lower() for r in potential_rows):
                    rows = potential_rows
                    break

        return rows

    def _parse_html_table(self, table_html: str) -> List[dict]:
        """Parse an HTML table into a list of row dictionaries."""
        rows = []

        # Parse header row
        header_pattern = re.compile(r'<thead>(.*?)</thead>', re.DOTALL | re.IGNORECASE)
        header_match = header_pattern.search(table_html)
        if not header_match:
            return rows

        header_html = header_match.group(1)
        headers = []
        for th_match in re.finditer(r'<th[^>]*>(.*?)</th>', header_html, re.DOTALL | re.IGNORECASE):
            header_text = re.sub(r'<[^>]+>', '', th_match.group(1)).strip()
            headers.append(header_text.lower())

        # Parse body rows
        body_pattern = re.compile(r'<tbody>(.*?)</tbody>', re.DOTALL | re.IGNORECASE)
        body_match = body_pattern.search(table_html)
        if not body_match:
            return rows

        body_html = body_match.group(1)

        for tr_match in re.finditer(r'<tr>(.*?)</tr>', body_html, re.DOTALL | re.IGNORECASE):
            tr_html = tr_match.group(1)
            cells = []
            for td_match in re.finditer(r'<td[^>]*>(.*?)</td>', tr_html, re.DOTALL | re.IGNORECASE):
                cell_html = td_match.group(1)
                # Replace <br> with pipe for splitting multiple entries
                cell_text = re.sub(r'<br\s*/?>.*?', ' | ', cell_html, flags=re.IGNORECASE)
                cell_text = re.sub(r'<[^>]+>', '', cell_text).strip()
                cells.append(cell_text)

            if len(cells) >= len(headers):
                row_dict = dict(zip(headers, cells))
                rows.append(row_dict)

        return rows

    def _process_markdown_row(self, row_data: dict) -> dict:
        """Process a single row from the markdown table.

        Returns dict with counts of municipalidades, delegados, and asignaciones created.
        """
        result = {'municipalidades': 0, 'delegados': 0, 'asignaciones': 0}

        # Extract row number (for logging)
        row_num = row_data.get('n°', row_data.get('#', '?')).strip('*')

        # Get municipalidad names - may be multiple separated by comma
        muni_names_cell = row_data.get('municipalidades distritales y provinciales', '')
        muni_names = self._split_municipalidad_names(muni_names_cell)

        if not muni_names:
            self._log(self.style.WARNING(f"  Row {row_num}: No municipalidades found, skipping"))
            return result

        # Get especialidad for this source (Ingeniería Eléctrica y Mecánica Eléctrica)
        try:
            especialidad = Especialidad.objects.get(nombre=MARKDOWN_SPECIALTY)
        except Especialidad.DoesNotExist:
            self._log(self.style.ERROR(f"  Especialidad {MARKDOWN_SPECIALTY} not found"))
            return result

        # Parse TITULAR delegate(s)
        titular_cip = self._normalize_cip(row_data.get('n° cip titular', ''))
        titular_name = row_data.get('delegado titular', '')

        if titular_cip and titular_name:
            # Split by ' | ' for multiple delegates in one cell
            titular_entries = self._split_delegate_entries(titular_cip, titular_name)
            for cip, name in titular_entries:
                d_result = self._process_markdown_delegate(cip, name, TipoDelegado.TITULAR, especialidad)
                result['delegados'] += d_result['delegados']

                # Create assignments for each municipalidad
                for muni_name in muni_names:
                    a_result = self._create_markdown_assignment(
                        muni_name, cip, TipoDelegado.TITULAR, especialidad
                    )
                    result['municipalidades'] += a_result['municipalidades']
                    result['asignaciones'] += a_result['asignaciones']

        # Parse ALTERNO delegate(s)
        alterno_cip = self._normalize_cip(row_data.get('n° cip alterno', ''))
        alterno_name = row_data.get('delegado alterno', '')

        if alterno_cip and alterno_name:
            # Split by ' | ' for multiple delegates in one cell
            alterno_entries = self._split_delegate_entries(alterno_cip, alterno_name)
            for cip, name in alterno_entries:
                d_result = self._process_markdown_delegate(cip, name, TipoDelegado.ALTERNO, especialidad)
                result['delegados'] += d_result['delegados']

                # Create assignments for each municipalidad
                for muni_name in muni_names:
                    a_result = self._create_markdown_assignment(
                        muni_name, cip, TipoDelegado.ALTERNO, especialidad
                    )
                    result['municipalidades'] += a_result['municipalidades']
                    result['asignaciones'] += a_result['asignaciones']

        return result

    def _split_municipalidad_names(self, cell_text: str) -> List[str]:
        """Split municipalidad cell text into individual names.

        Handles grouped municipalidad rows (rows 44-50) where multiple
        municipalities are listed in one cell separated by commas.
        """
        if not cell_text:
            return []

        # Split by comma and clean up
        names = []
        for name in cell_text.split(','):
            name = name.strip()
            # Skip empty entries and "PROVINCIAL DE..." prefixes for individual names
            if name and name.upper() not in ('PROVINCIAL', 'PROVINCIA'):
                names.append(name)

        return names

    def _split_delegate_entries(self, cip: str, name: str) -> List[Tuple[str, str]]:
        """Split a cell with multiple delegates separated by ' | ' (from <br> conversion).

        Returns list of (cip, name) tuples.
        """
        entries = []

        # Split by ' | ' which comes from <br> replacement
        cip_parts = [c.strip() for c in cip.split(' | ')]
        name_parts = [n.strip() for n in name.split(' | ')]

        # If we have multiple CIPs but maybe single name (rare case)
        if len(cip_parts) > 1:
            # Pair them up - zip will stop at the shorter list
            for c, n in zip(cip_parts, name_parts):
                if c:
                    entries.append((c, n))
        elif cip:
            entries.append((cip, name))
        elif name:
            # No CIP but has name - this is an error case
            self._log(self.style.WARNING(f"    No CIP found for delegate: {name}"))

        return entries

    def _process_markdown_delegate(self, cip: str, full_name: str, tipo: str, especialidad) -> dict:
        """Create or find PerfilIngeniero and Delegado for a markdown source delegate.

        Returns dict with counts.
        """
        result = {'delegados': 0}

        if not cip or not full_name:
            return result

        # Normalize CIP
        normalized_cip = self._normalize_cip(cip)
        if not normalized_cip:
            self._log(self.style.WARNING(f"    Invalid CIP: {cip} for {full_name}"))
            return result

        # Parse name: "APELLIDO_PATERNO APELLIDO_MATERNO NOMBRES"
        name_parts = self._parse_delegate_name(full_name)

        if self.dry_run:
            self._log(f"    [DRY-RUN] Would create/find PerfilIngeniero CIP={normalized_cip}: {full_name}")
            self._log(f"    [DRY-RUN] Would create/find Delegado: {full_name} (CIP={normalized_cip}, tipo={tipo})")
            result['delegados'] = 1
            return result

        # Get or create PerfilIngeniero
        perfil, perfil_created = self._get_or_create_perfil_markdown(
            normalized_cip, name_parts
        )

        if not perfil:
            self._log(self.style.ERROR(f"    Failed to get/create PerfilIngeniero for CIP {normalized_cip}"))
            return result

        # Get or create Delegado (tipo is now set on MunicipalidadaDelegado, not on Delegado)
        try:
            delegado, created = Delegado.objects.update_or_create(
                perfil_ingeniero=perfil,
                defaults={
                    'especialidad': especialidad,
                    'banco': None,
                    'status': DelegadoStatus.ACTIVO,
                }
            )
            if created:
                result['delegados'] = 1
                self._log(f"    Created delegado: {full_name} (CIP={normalized_cip})")
                PeriodoDelegado.objects.get_or_create(
                    delegado=delegado,
                    periodo_inicio=timezone.now().date(),
                    defaults={'periodo_fin': None},
                )
            # No update for tipo since it's no longer on Delegado
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating Delegado: {e}"))

        return result

    def _get_or_create_perfil_markdown(self, cip: str, name_parts: dict) -> Tuple[Optional[PerfilIngeniero], bool]:
        """Get or create PerfilIngeniero from markdown data.

        Returns (perfil, created) tuple.
        """
        try:
            perfil = PerfilIngeniero.objects.get(cip=cip)
            # Update name if different
            updated = False
            for field in ['nombres', 'apellido_paterno', 'apellido_materno']:
                if name_parts.get(field) and getattr(perfil, field) != name_parts[field]:
                    setattr(perfil, field, name_parts[field])
                    updated = True
            if updated:
                try:
                    perfil.save()
                    self._log(f"    Updated PerfilIngeniero: {perfil.nombre_completo}")
                except Exception as e:
                    self._log(self.style.WARNING(f"    Error updating PerfilIngeniero: {e}"))
            return perfil, False
        except PerfilIngeniero.DoesNotExist:
            pass

        if self.dry_run:
            return None, True

        try:
            perfil = PerfilIngeniero.objects.create(
                cip=cip,
                nombres=name_parts.get('nombres', ''),
                apellido_paterno=name_parts.get('apellido_paterno', ''),
                apellido_materno=name_parts.get('apellido_materno', ''),
            )
            self._log(f"    Created PerfilIngeniero: {perfil.nombre_completo} (CIP={cip})")
            return perfil, True
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating PerfilIngeniero: {e}"))
            return None, False

    def _parse_delegate_name(self, full_name: str) -> dict:
        """Parse delegate full name into components.

        Format expected: "APELLIDO_PATERNO APELLIDO_MATERNO NOMBRES"
        Handles Greek characters (ΜANSILLA, ΑΝΤΟΝΙΟ) by normalizing.

        Returns dict with 'nombres', 'apellido_paterno', 'apellido_materno'.
        """
        # Normalize Greek and other unicode characters
        name = self._normalize_unicode_name(full_name)

        # Split by spaces
        parts = name.split()

        if len(parts) >= 3:
            # First two parts are surnames, rest is nombres
            apellido_paterno = parts[0]
            apellido_materno = parts[1]
            nombres = ' '.join(parts[2:])
        elif len(parts) == 2:
            # Could be "APELLIDO NOMBRES" where apellido is combined
            apellido_paterno = parts[0]
            apellido_materno = ''
            nombres = parts[1]
        elif len(parts) == 1:
            apellido_paterno = parts[0]
            apellido_materno = ''
            nombres = ''
        else:
            apellido_paterno = ''
            apellido_materno = ''
            nombres = ''

        return {
            'nombres': nombres,
            'apellido_paterno': apellido_paterno,
            'apellido_materno': apellido_materno,
        }

    def _normalize_unicode_name(self, name: str) -> str:
        """Normalize unicode characters in names (Greek letters, etc).

        Handles cases like ΜANSILLA, ΑΝΤΟΝΙΟ by replacing Greek letters
        with their Latin equivalents when possible.
        """
        # Greek to Latin mapping for common Greek letters found in names
        greek_to_latin = {
            'Α': 'A', 'Β': 'B', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Θ': 'TH',
            'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M', 'Ν': 'N', 'Ξ': 'X', 'Ο': 'O', 'Π': 'P',
            'Ρ': 'R', 'Σ': 'S', 'Τ': 'T', 'Υ': 'Y', 'Φ': 'F', 'Χ': 'CH', 'Ψ': 'PS', 'Ω': 'O',
            'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'h', 'θ': 'th',
            'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x', 'ο': 'o', 'π': 'p',
            'ρ': 'r', 'σ': 's', 'τ': 't', 'υ': 'y', 'φ': 'f', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
        }

        result = []
        for char in name:
            result.append(greek_to_latin.get(char, char))

        return ''.join(result)

    def _create_markdown_assignment(
        self,
        muni_nombre: str,
        cip: str,
        tipo: str,
        especialidad
    ) -> dict:
        """Create or update municipalidad and its assignment to a delegado.

        Returns dict with counts of municipalidades and asignaciones.
        """
        result = {'municipalidades': 0, 'asignaciones': 0}

        if not muni_nombre or not cip:
            return result

        normalized_cip = self._normalize_cip(cip)
        if not normalized_cip:
            return result

        if self.dry_run:
            self._log(f"    [DRY-RUN] Would create/find municipalidad: {muni_nombre}")
            self._log(f"    [DRY-RUN] Would assign delegado CIP={normalized_cip} to {muni_nombre} (tipo={tipo})")
            result['municipalidades'] = 1
            result['asignaciones'] = 1
            return result

        # Find or create municipalidad with ELE prefix
        muni_code = self._generate_municipalidad_code(muni_nombre)

        municipalidad, muni_created = self._get_or_create_municipalidad_markdown(
            muni_nombre, muni_code
        )

        if not municipalidad:
            return result

        if muni_created:
            result['municipalidades'] = 1

        # Find the delegado by CIP
        try:
            delegado = Delegado.objects.select_related('perfil_ingeniero').get(
                perfil_ingeniero__cip=normalized_cip
            )
        except Delegado.DoesNotExist:
            self._log(self.style.WARNING(
                f"    Delegado not found for CIP {normalized_cip} when creating assignment for {muni_nombre}"
            ))
            return result

        # Create assignment (tipo now goes on MunicipalidadaDelegado, not Delegado)
        # categoria is always Edificaciones for markdown source (Ingeniería Eléctrica y Mecánica Eléctrica - Edificaciones)
        try:
            _, asig_created = MunicipalidadDelegado.objects.update_or_create(
                delegado=delegado,
                municipalidad=municipalidad,
                defaults={
                    'activo': True,
                    'tipo': tipo,
                    'categoria': CategoriaDelegado.EDIFICACIONES,
                },
            )
            result['asignaciones'] = 1
            if asig_created:
                self._log(f"    Created asignación: {delegado.perfil_ingeniero.cip} @ {municipalidad.nombre} ({tipo})")
        except Exception as e:
            self._log(self.style.WARNING(f"    Error creating asignación: {e}"))

        return result

    def _generate_municipalidad_code(self, nombre: str) -> str:
        """Generate a unique municipalidad code with ELE prefix.

        For markdown source, new municipalidades get 'ELE' prefix followed by
        a hash of the name to ensure uniqueness.
        """
        # Create a simple hash from the name
        name_hash = abs(hash(nombre.upper())) % 100000
        return f"{MARKDOWN_MUNICIPALIDAD_CODE_PREFIX}{name_hash:05d}"

    def _get_or_create_municipalidad_markdown(self, nombre: str, code: str) -> Tuple[Optional[Municipalidad], bool]:
        """Get or create a municipalidad for markdown source.

        First tries to find by exact name, then by code prefix.

        Returns (municipalidad, created) tuple.
        """
        # First try to find by exact name
        municipalidad = Municipalidad.objects.filter(nombre__iexact=nombre).first()
        if municipalidad:
            return municipalidad, False

        # Try to find by code (in case it was created before)
        if code:
            municipalidad = Municipalidad.objects.filter(codigo=code).first()
            if municipalidad:
                # Update name if different
                if municipalidad.nombre != nombre:
                    municipalidad.nombre = nombre
                    municipalidad.save(update_fields=['nombre'])
                return municipalidad, False

        # Create new
        try:
            # Find a unique code
            base_code = code
            counter = 1
            while Municipalidad.objects.filter(codigo=code).exists():
                code = f"{base_code[:3]}{counter:04d}"
                counter += 1
                if counter > 1000:
                    break

            municipalidad = Municipalidad.objects.create(
                codigo=code,
                nombre=nombre,
                activo=True,
            )
            self._log(f"    Created municipalidad: {nombre} (code={code})")
            return municipalidad, True
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating municipalidad {nombre}: {e}"))
            return None, False
