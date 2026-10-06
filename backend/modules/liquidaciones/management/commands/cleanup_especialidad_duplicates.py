"""
Management command to clean up duplicate Especialidad records caused by
accented/unaccented name mismatches.

Usage:
    python manage.py cleanup_especialidad_duplicates --settings=config.settings.development
    python manage.py cleanup_especialidad_duplicates --dry-run --settings=config.settings.development

What it does:
1. Identifies unaccented duplicates of the canonical accented Especialidad records.
2. Repoints any FK/M2M references (Delegado.especialidad, TarifaLiquidacionBase.especialidades M2M)
   from duplicates to their canonical accented counterparts.
3. Deletes the unaccented duplicates after references are moved.
4. Reports what was done and any remaining issues.

Canonical (authoritative) names are the accented forms:
    - Ingeniería Civil
    - Ingeniería Sanitaria
    - Ingeniería Eléctrica y Mecánica Eléctrica
"""

import unicodedata
import logging

from django.core.management.base import BaseCommand, CommandError

from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadIngeniero as Especialidad
from modules.liquidaciones.domain.models.delegado import Delegado
from modules.liquidaciones.domain.models.liquidacion.liquidacion import TarifaLiquidacionBase


logger = logging.getLogger(__name__)


def normalize_specialty_name(name: str) -> str:
    """Remove accents/diacritics from a specialty name for canonical comparison."""
    if not name:
        return name
    normalized = unicodedata.normalize('NFD', name)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')


CANONICAL_SPECIALTY_NAMES = [
    'Ingeniería Civil',
    'Ingeniería Sanitaria',
    'Ingeniería Eléctrica y Mecánica Eléctrica',
]

SPECIALTY_NORMALIZATION_MAP = {
    'ingenieria civil': 'Ingeniería Civil',
    'ingenieria sanitaria': 'Ingeniería Sanitaria',
    'ingenieria electrica y mecanica electrica': 'Ingeniería Eléctrica y Mecánica Eléctrica',
}


def get_canonical_specialty_name(raw_name: str) -> str:
    """Return the canonical accented specialty name for a raw name."""
    if not raw_name:
        return raw_name
    normalized = normalize_specialty_name(raw_name).lower()
    return SPECIALTY_NORMALIZATION_MAP.get(normalized, raw_name)


class Command(BaseCommand):
    help = "Clean up duplicate Especialidad records caused by accent/unaccent name variants"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']

        self._log(f"\n[cleanup_especialidad_duplicates] Starting...")

        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE - No database writes will occur"))

        # Step 1: Identify all Especialidad records
        all_especialidades = list(Especialidad.objects.all())
        self._log(f"\n  Found {len(all_especialidades)} Especialidad records total")

        # Step 2: Group by canonical (normalized) name
        by_canonical = {}  # canonical_lower -> list of (esp, original_name)
        for esp in all_especialidades:
            canonical = get_canonical_specialty_name(esp.nombre)
            key = canonical.lower()
            if key not in by_canonical:
                by_canonical[key] = {'canonical': canonical, 'records': []}
            by_canonical[key]['records'].append(esp)

        # Step 3: Find duplicates (more than one record with same canonical name)
        duplicates = {k: v for k, v in by_canonical.items() if len(v['records']) > 1}
        clean = {k: v for k, v in by_canonical.items() if len(v['records']) == 1}

        self._log(f"  Canonical groups with NO duplicates: {len(clean)}")
        self._log(f"  Canonical groups WITH duplicates: {len(duplicates)}")

        if not duplicates and not self.dry_run:
            self._log(self.style.SUCCESS("\n  No duplicates found. Database is clean."))
            return

        # Step 4: For each duplicate group, determine canonical (keep) vs duplicate (remove)
        for key, group in duplicates.items():
            canonical_name = group['canonical']
            records = group['records']
            self._log(f"\n  Processing duplicate group: canonical='{canonical_name}'")
            for esp in records:
                self._log(f"    Record ID={esp.id} nombre={repr(esp.nombre)}")

        # Step 5: Repoint references and delete duplicates
        total_delegado_refs_moved = 0
        total_tarifa_m2m_refs_moved = 0
        duplicates_deleted = 0

        for key, group in duplicates.items():
            canonical_name = group['canonical']
            records = group['records']

            # Find the canonical record (the accented one, or first if all same)
            canonical_esp = None
            duplicate_records = []

            for esp in records:
                if esp.nombre == canonical_name:
                    canonical_esp = esp
                else:
                    duplicate_records.append(esp)

            if not canonical_esp:
                # None has exact canonical name - pick the first one as canonical
                canonical_esp = records[0]
                duplicate_records = records[1:]
                self._log(self.style.WARNING(
                    f"    No exact match for '{canonical_name}', "
                    f"keeping ID={canonical_esp.id} ({repr(canonical_esp.nombre)}) as canonical"
                ))

            self._log(f"\n  Canonical: ID={canonical_esp.id} nombre={repr(canonical_esp.nombre)}")
            self._log(f"  Duplicates to remove: {[r.id for r in duplicate_records]}")

            for dup in duplicate_records:
                # Repoint Delegado FKs
                dele_refs = Delegado.objects.filter(especialidad=dup)
                dele_count = dele_refs.count()
                if dele_count > 0:
                    self._log(f"    Moving {dele_count} Delegado FK(s) from {dup.id} to {canonical_esp.id}")
                    if not self.dry_run:
                        dele_refs.update(especialidad=canonical_esp)
                    total_delegado_refs_moved += dele_count

                # Repoint TarifaLiquidacionBase M2M
                tarifa_bases = TarifaLiquidacionBase.objects.filter(especialidades=dup)
                tarifa_count = tarifa_bases.count()
                if tarifa_count > 0:
                    self._log(f"    Moving {tarifa_count} TarifaLiquidacionBase M2M(s) from {dup.id} to {canonical_esp.id}")
                    if not self.dry_run:
                        for tb in tarifa_bases:
                            tb.especialidades.remove(dup)
                            tb.especialidades.add(canonical_esp)
                    total_tarifa_m2m_refs_moved += tarifa_count

                # Delete duplicate
                self._log(f"    Deleting duplicate Especialidad ID={dup.id} nombre={repr(dup.nombre)}")
                if not self.dry_run:
                    dup.delete()
                    self._log(self.style.SUCCESS(f"    Deleted ID={dup.id}"))
                duplicates_deleted += 1

        # Step 6: Report final state
        self._log(self.style.SUCCESS(
            f"\n[cleanup_especialidad_duplicates] {'DRY-RUN summary: would have ' if self.dry_run else ''}Completed:"
        ))
        self._log(f"  Duplicate groups processed: {len(duplicates)}")
        self._log(f"  Duplicates deleted: {duplicates_deleted}")
        self._log(f"  Delegado FK references moved: {total_delegado_refs_moved}")
        self._log(f"  TarifaLiquidacionBase M2M references moved: {total_tarifa_m2m_refs_moved}")

        # Final state report
        remaining = list(Especialidad.objects.all())
        self._log(f"\n  Remaining Especialidad records: {len(remaining)}")
        for esp in remaining:
            dele_count = Delegado.objects.filter(especialidad=esp).count()
            tarifa_count = TarifaLiquidacionBase.objects.filter(especialidades=esp).count()
            self._log(f"    ID={esp.id} nombre={repr(esp.nombre)} Delegado={dele_count} TarifaM2M={tarifa_count}")

    def _log(self, msg):
        """Log message safely, handling encoding issues on Windows."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            safe_msg = msg.encode('ascii', 'replace').decode('ascii')
            self.stdout.write(safe_msg)
