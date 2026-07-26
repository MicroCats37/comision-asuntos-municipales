"""
Management command to seed tarifas de edificación.

Usage:
    python manage.py seed_tarifas_edificacion --settings=config.settings.development
    python manage.py seed_tarifas_edificacion --dry-run --settings=config.settings.development

Seed data:
    backend/modules/liquidaciones/seeds/tarifas_edificacion.json

Creates:
    - TarifaLiquidacionBase records (EDIFICACION tipo_liquidacion)
    - TarifaPorcentajeObra detail records
    - ReglaTarifaEdificacion mappings
    - Especialidad records if missing (using exact nombre match)
"""

import json
import logging
import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError

from modules.liquidaciones.domain.models.liquidacion.liquidacion import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    ReglaTarifaEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.tarifas_reglas import (
    ReglaTarifaLiquidacion,
)
from modules.liquidaciones.domain.models.especialidades import Especialidad
from modules.liquidaciones.domain.constants import TipoLiquidacion, TipoTramiteEdificaciones, TramiteAccion


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
    normalized = normalize_specialty_name(raw_name).lower()
    return SPECIALTY_NORMALIZATION_MAP.get(normalized, raw_name)


class Command(BaseCommand):
    help = "Seed tarifas de edificación (tarifa base + porcentaje + reglas)"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validar datos seed sin escribir en la base de datos',
        )
        parser.add_argument(
            '--seed-path',
            type=str,
            default=None,
            help='Ruta al archivo JSON seed de tarifas',
        )
        parser.add_argument(
            '--liquidaciones',
            type=str,
            default=None,
            help=(
                'Tipos de liquidacion a procesar (comma-separated). '
                'Ej: "EDIFICACION" (default) o "IMPACTO_VIAL,TALUDES". '
                'Cuando se especifica, solo esos tipos seran eliminados y seeded.'
            ),
        )
        parser.add_argument(
            '--skip-delete',
            action='store_true',
            help='Omite la eliminacion de tarifas existentes (solo hace seeding)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.seed_path = (
            Path(options['seed_path'])
            if options['seed_path']
            else self.SEEDS_DIR / "tarifas_edificacion.json"
        )
        liquidaciones_raw = options.get('liquidaciones')
        self.skip_delete = options.get('skip_delete', False)

        # Parse liquidation types to process
        if liquidaciones_raw:
            self.liquidaciones_to_process = [
                lt.strip().upper() for lt in liquidaciones_raw.split(',') if lt.strip()
            ]
        else:
            self.liquidaciones_to_process = [TipoLiquidacion.EDIFICACION]

        self._log(f"\n[seed_tarifas_edificacion] Starting...")
        self._log(f"  Liquidaciones to process: {self.liquidaciones_to_process}")
        if self.skip_delete:
            self._log(self.style.WARNING("  SKIP-DELETE MODE - No existing tariffs will be deleted"))
        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE - No database writes will occur"))

        # Load seed data
        seed_data = self._load_seed()
        if not seed_data:
            raise CommandError("Failed to load seed data")

        # STEP 1: Delete existing tariffs for target liquidation types (unless dry-run or skip-delete)
        if not self.dry_run and not self.skip_delete:
            deleted_reglas_liq, deleted_reglas_edif, deleted_tarifas = self._delete_existing_tariffs()
            self._log(f"  Deleted {deleted_reglas_liq} ReglaTarifaLiquidacion records")
            self._log(f"  Deleted {deleted_reglas_edif} ReglaTarifaEdificacion records")
            self._log(f"  Deleted {deleted_tarifas} TarifaLiquidacionBase records "
                      f"(and their TarifaPorMetroCuadrado / TarifaPorcentajeObra via CASCADE)")
        else:
            if self.dry_run:
                self._log(f"  [DRY-RUN] Would delete existing tariffs for: {self.liquidaciones_to_process}")
            else:
                self._log(f"  [SKIP-DELETE] Skipped deletion of existing tariffs")

        # STEP 2: Process tarifas from seed JSON (filtered to target liquidation types)
        tarifas_created = 0
        tarifas_updated = 0
        reglas_created = 0
        reglas_updated = 0
        especialidades_ensured = 0
        skipped_not_in_scope = 0

        for tarifa_data in seed_data.get('tarifas', []):
            tipo_liq = tarifa_data.get('tipo_liquidacion', 'EDIFICACION')
            if tipo_liq not in self.liquidaciones_to_process:
                skipped_not_in_scope += 1
                continue
            result = self._process_tarifa(tarifa_data)
            if result['tarifa_created']:
                tarifas_created += 1
            else:
                tarifas_updated += 1
            if result['regla_created']:
                reglas_created += 1
            else:
                reglas_updated += 1
            especialidades_ensured += result['especialidades_ensured']

        # Report gaps
        notas = seed_data.get('notas', [])
        if notas:
            self._log(self.style.WARNING("\n  [NOTAS/GAPS]"))
            for nota in notas:
                self._log(f"    - {nota}")

        self._log(self.style.SUCCESS(
            f"\n[seed_tarifas_edificacion] Completed:"
        ))
        self._log(f"  Liquidaciones processed: {self.liquidaciones_to_process}")
        self._log(f"  Tarifas: {tarifas_created} created, {tarifas_updated} updated")
        self._log(f"  Reglas: {reglas_created} created, {reglas_updated} updated")
        self._log(f"  Especialidades ensured: {especialidades_ensured}")
        if skipped_not_in_scope > 0:
            self._log(f"  Skipped (not in scope): {skipped_not_in_scope}")

    def _delete_existing_tariffs(self):
        """
        Delete all existing tariffs for the configured liquidation types.

        This deletes for each tipo_liquidacion in self.liquidaciones_to_process:
        1. All ReglaTarifaLiquidacion records (old m2 rule system)
        2. All ReglaTarifaEdificacion records (percentage rule system)
        3. All TarifaLiquidacionBase records — CASCADE deletes:
           - TarifaPorMetroCuadrado (OneToOne)
           - TarifaPorcentajeObra (OneToOne)
           - LiquidacionPorMetroCuadrado (FK from TarifaPorMetroCuadrado CASCADE)

        Returns (deleted_reglas_liq_count, deleted_reglas_edif_count, deleted_tarifas_count).
        """
        total_reglas_liq = 0
        total_reglas_edif = 0
        total_tarifas = 0

        for tipo_liq in self.liquidaciones_to_process:
            self._log(f"    Processing deletion for: {tipo_liq}")

            # Count before deletion
            reglas_liq_count = ReglaTarifaLiquidacion.objects.filter(
                tarifa_base__tipo_liquidacion=tipo_liq
            ).count()
            reglas_edif_count = ReglaTarifaEdificacion.objects.filter(
                tarifa_base__tipo_liquidacion=tipo_liq
            ).count()
            bases = TarifaLiquidacionBase.objects.filter(tipo_liquidacion=tipo_liq)
            bases_count = bases.count()

            # Delete ReglaTarifaLiquidacion for this type
            deleted_liq, _ = ReglaTarifaLiquidacion.objects.filter(
                tarifa_base__tipo_liquidacion=tipo_liq
            ).delete()
            total_reglas_liq += deleted_liq

            # Delete ReglaTarifaEdificacion for this type
            deleted_edif, _ = ReglaTarifaEdificacion.objects.filter(
                tarifa_base__tipo_liquidacion=tipo_liq
            ).delete()
            total_reglas_edif += deleted_edif

            # Delete TarifaLiquidacionBase (CASCADE deletes TarifaPorMetroCuadrado,
            # TarifaPorcentajeObra, and LiquidacionPorMetroCuadrado via FK CASCADE)
            deleted_bases, _ = bases.delete()
            total_tarifas += deleted_bases

            self._log(self.style.WARNING(
                f"      Cleared {deleted_liq} ReglaTarifaLiquidacion, "
                f"{deleted_edif} ReglaTarifaEdificacion, "
                f"{deleted_bases} TarifaLiquidacionBase "
                f"(plus cascade-deleted TarifaPorMetroCuadrado/TarifaPorcentajeObra/"
                f"LiquidacionPorMetroCuadrado)"
            ))

        return total_reglas_liq, total_reglas_edif, total_tarifas

    def _log(self, msg):
        """Registra mensaje de forma segura, manejando problemas de codificación en Windows."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
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
            self._log(f"  Descripcion: {data.get('descripcion', 'N/A')}")
            return data
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in seed file: {e}")

    def _ensure_especialidades(self, especialidad_nombres):
        """Ensure all especialidades exist, creating if needed.

        Canonicalizes unaccented names from seed data to the accented canonical form
        before get_or_create, preventing duplicate Especialidad records with
        accent/unaccent name variants.

        Returns count of especialidades created.
        """
        created_count = 0
        for raw_nombre in especialidad_nombres:
            # Canonicalize to accented form before DB operation
            nombre = get_canonical_specialty_name(raw_nombre)
            if self.dry_run:
                self._log(f"    [DRY-RUN] Would create/find especialidad: {nombre} (from '{raw_nombre}')")
                continue

            spec, created = Especialidad.objects.get_or_create(
                nombre=nombre,
                defaults={}
            )
            if created:
                self._log(self.style.SUCCESS(f"    Created especialidad: {nombre}"))
                created_count += 1
            else:
                self._log(f"    Found existing especialidad: {nombre}")

        return created_count if not self.dry_run else len(especialidad_nombres)

    def _get_especialidades(self, especialidad_nombres):
        """Get Especialidad objects by canonical nombre match.

        Canonicalizes names before lookup. Raises if canonical specialty not found.
        """
        especialidades = []
        for raw_nombre in especialidad_nombres:
            # Canonicalize to accented form before DB lookup
            nombre = get_canonical_specialty_name(raw_nombre)
            try:
                spec = Especialidad.objects.get(nombre=nombre)
                especialidades.append(spec)
            except Especialidad.DoesNotExist:
                raise CommandError(
                    f"Especialidad '{nombre}' (from raw '{raw_nombre}') not found. "
                    f"Run load_delegados_reales first to create especialidades."
                )
        return especialidades

    def _process_tarifa(self, tarifa_data):
        """Process a single tarifa entry from seed.

        Returns dict with counts.
        """
        result = {
            'tarifa_created': False,
            'regla_created': False,
            'especialidades_ensured': 0,
        }

        tipo_liquidacion = tarifa_data.get('tipo_liquidacion', 'EDIFICACION')
        periodo_inicio_str = tarifa_data.get('periodo_inicio', '2026-01-01')
        periodo_fin_str = tarifa_data.get('periodo_fin')
        especialidad_nombres = tarifa_data.get('especialidades', [])
        porcentaje_liquidacion = Decimal(str(tarifa_data.get('porcentaje_liquidacion', '0')))
        derecho_minimo = Decimal(str(tarifa_data.get('derecho_minimo', '0')))
        derecho_maximo_str = tarifa_data.get('derecho_maximo')
        porcentaje_minimo_uit = Decimal(str(tarifa_data.get('porcentaje_minimo_uit', '0.02')))
        reglas = tarifa_data.get('reglas', [])

        periodo_inicio = date.fromisoformat(periodo_inicio_str)
        periodo_fin = None if periodo_fin_str is None else date.fromisoformat(periodo_fin_str)
        derecho_maximo = None if derecho_maximo_str is None else Decimal(str(derecho_maximo_str))

        # Ensure especialidades exist
        result['especialidades_ensured'] = self._ensure_especialidades(especialidad_nombres)

        # Get Especialidad objects
        especialidades = self._get_especialidades(especialidad_nombres)

        if self.dry_run:
            self._log(f"\n  [DRY-RUN] Would create/update TarifaLiquidacionBase:")
            self._log(f"    tipo_liquidacion={tipo_liquidacion}, periodo_inicio={periodo_inicio}")
            self._log(f"    especialidades={especialidad_nombres}")
            self._log(f"    porcentaje_liquidacion={porcentaje_liquidacion}, derecho_minimo={derecho_minimo}")
            for regla in reglas:
                self._log(f"    [DRY-RUN] Would create ReglaTarifaEdificacion: {regla}")
            result['tarifa_created'] = True
            result['regla_created'] = True
            return result

        # Create/update TarifaLiquidacionBase
        # Key: tipo_liquidacion + periodo_inicio + hash of (sorted especialidad nombres, porcentaje_liquidacion)
        # Different percentage rates for the same specialty set must NOT share a base,
        # otherwise TarifaPorcentajeObra.update_or_create would overwrite the previous percentage.
        sorted_specs = sorted(especialidad_nombres)
        spec_hash = hash((tuple(sorted_specs), str(porcentaje_liquidacion)))

        # Look for an existing base with same tipo_liquidacion, periodo_inicio,
        # AND same set of especialidades AND same percentage (checked via M2M count + names
        # and via TarifaPorcentajeObra.porcentaje_liquidacion).
        existing_bases = TarifaLiquidacionBase.objects.filter(
            tipo_liquidacion=tipo_liquidacion,
            periodo_inicio=periodo_inicio,
        ).prefetch_related('especialidades', 'detalle_porcentual')

        tarifa_base = None
        tarifa_created = False
        for candidate in existing_bases:
            candidate_specs = sorted(candidate.especialidades.values_list('nombre', flat=True))
            candidate_pct = getattr(candidate.detalle_porcentual, 'porcentaje_liquidacion', None)
            if list(candidate_specs) == sorted_specs and candidate_pct == porcentaje_liquidacion:
                tarifa_base = candidate
                tarifa_created = False
                break

        if tarifa_base is None:
            tarifa_base = TarifaLiquidacionBase.objects.create(
                tipo_liquidacion=tipo_liquidacion,
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
            )
            tarifa_created = True

        if tarifa_created:
            self._log(self.style.SUCCESS(f"    Created TarifaLiquidacionBase: {tarifa_base}"))
            result['tarifa_created'] = True
        else:
            self._log(f"    Found existing TarifaLiquidacionBase: {tarifa_base}")

        # Sync especialidades M2M
        tarifa_base.especialidades.set(especialidades)

        # Create/update TarifaPorcentajeObra
        # Note: nullable FK during transition, but we create with FK set
        porcentaje_obra, porcentaje_created = TarifaPorcentajeObra.objects.update_or_create(
            tarifa_base=tarifa_base,
            defaults={
                'porcentaje_liquidacion': porcentaje_liquidacion,
                'derecho_minimo': derecho_minimo,
                'derecho_maximo': derecho_maximo,
                'porcentaje_minimo_uit': porcentaje_minimo_uit,
            },
        )

        if porcentaje_created:
            self._log(self.style.SUCCESS(
                f"    Created TarifaPorcentajeObra: {porcentaje_liquidacion} (min: {derecho_minimo})"
            ))
        else:
            self._log(f"    Updated TarifaPorcentajeObra: {porcentaje_liquidacion} (min: {derecho_minimo})")

        # Create/update ReglaTarifaEdificacion entries
        for regla_data in reglas:
            tipo_tramite = regla_data.get('tipo_tramite')
            tramite_accion = regla_data.get('tramite_accion')

            if not tipo_tramite or not tramite_accion:
                self._log(self.style.WARNING(
                    f"    Skipping rule with missing tipo_tramite or tramite_accion: {regla_data}"
                ))
                continue

            # Validate enum values
            valid_tipo_tramite = self._validate_choice(
                tipo_tramite, TipoTramiteEdificaciones, 'TipoTramiteEdificaciones'
            )
            valid_tramite_accion = self._validate_choice(
                tramite_accion, TramiteAccion, 'TramiteAccion'
            )

            if not valid_tipo_tramite or not valid_tramite_accion:
                self._log(self.style.WARNING(
                    f"    Skipping invalid rule: tipo_tramite={tipo_tramite}, tramite_accion={tramite_accion}"
                ))
                continue

            regla, regla_created = ReglaTarifaEdificacion.objects.update_or_create(
                tipo_tramite=valid_tipo_tramite,
                tramite_accion=valid_tramite_accion,
                tarifa_base=tarifa_base,
                defaults={},
            )

            if regla_created:
                self._log(self.style.SUCCESS(
                    f"    Created ReglaTarifaEdificacion: {valid_tipo_tramite}/{valid_tramite_accion}"
                ))
                result['regla_created'] = True
            else:
                self._log(f"    Found existing ReglaTarifaEdificacion: {valid_tipo_tramite}/{valid_tramite_accion}")

        return result

    def _validate_choice(self, value, choice_class, choice_name):
        """Validate that a value is a valid Django TextChoices value.

        Returns the valid value if valid, None otherwise.
        """
        # Check if value is in the choice values
        valid_values = [c.value for c in choice_class]
        if value in valid_values:
            return value

        # Try case-insensitive match
        for valid_value in valid_values:
            if valid_value.upper() == value.upper():
                self._log(self.style.WARNING(
                    f"    Case mismatch in {choice_name}: '{value}' -> '{valid_value}'"
                ))
                return valid_value

        self._log(self.style.ERROR(
            f"    Invalid {choice_name} value: '{value}'. Valid: {valid_values}"
        ))
        return None
