"""
Management command to normalize existing LiquidacionSnapshot JSON data.

This migrates old format snapshots (with flat municipalidad_id/municipalidad_nombre
and numero_revision in each revision) to the new format (nested municipalidad object
and numero_revision only at edificaciones level).

Usage:
    python manage.py normalize_liquidacion_snapshots [--dry-run]
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.liquidaciones.models import LiquidacionSnapshot


class Command(BaseCommand):
    help = "Normalize existing LiquidacionSnapshot JSON data to new structure"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )

    def _normalize_snapshot(self, snapshot: LiquidacionSnapshot) -> tuple[bool, dict]:
        """
        Normalize a single snapshot to the new format.
        
        Returns:
            (was_modified, normalized_data)
        """
        data = snapshot.data
        if not data:
            return False, data

        modified = False
        normalized = dict(data)

        # 1. Normalize liquidacion.municipalidad (flat -> nested object)
        liquidacion = normalized.get("liquidacion", {})
        if liquidacion:
            muni = liquidacion.get("municipalidad")
            # Check if already in new format (nested object with 'provincia' and 'distrito')
            if isinstance(muni, dict) and ("provincia" in muni or "distrito" in muni or "codigo" in muni):
                # Already in new format
                pass
            elif isinstance(muni, dict) and "id" in muni:
                # Already in new format (simple)
                pass
            else:
                # Old flat format: municipalidad_id and municipalidad_nombre
                old_id = liquidacion.pop("municipalidad_id", None)
                old_nombre = liquidacion.pop("municipalidad_nombre", None)
                if old_id or old_nombre:
                    liquidacion["municipalidad"] = {
                        "id": old_id,
                        "nombre": old_nombre or "",
                        "codigo": None,
                        "provincia": None,
                        "distrito": None,
                    }
                    modified = True
                elif "municipalidad" not in liquidacion:
                    # No municipalidad data at all, create empty
                    liquidacion["municipalidad"] = {
                        "id": None,
                        "nombre": "",
                        "codigo": None,
                        "provincia": None,
                        "distrito": None,
                    }

            normalized["liquidacion"] = liquidacion

        # 2. Normalize proyecto.distrito (add if missing)
        proyecto = liquidacion.get("proyecto", {})
        if proyecto and "distrito" not in proyecto:
            proyecto["distrito"] = None
            modified = True
            normalized["liquidacion"]["proyecto"] = proyecto

        # 3. Normalize edificaciones.revisiones[] (remove numero_revision from each item)
        edificaciones = normalized.get("edificaciones", {})
        if edificaciones:
            revisiones = edificaciones.get("revisiones", [])
            if revisiones:
                for rev in revisiones:
                    if "numero_revision" in rev:
                        del rev["numero_revision"]
                        modified = True

        return modified, normalized

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbosity = options["verbosity"]

        snapshots = LiquidacionSnapshot.objects.all()
        total = snapshots.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No snapshots found to normalize."))
            return

        self.stdout.write(f"Found {total} snapshots to check.")

        modified_count = 0
        error_count = 0

        for snapshot in snapshots:
            try:
                was_modified, normalized = self._normalize_snapshot(snapshot)

                if was_modified:
                    if verbosity >= 1:
                        self.stdout.write(
                            f"  Snapshot {snapshot.id}: needs normalization"
                        )

                    if not dry_run:
                        with transaction.atomic():
                            snapshot.data = normalized
                            snapshot.save(update_fields=["data"])
                            modified_count += 1
                    else:
                        modified_count += 1
            except Exception as e:
                error_count += 1
                self.stderr.write(
                    self.style.ERROR(f"  Snapshot {snapshot.id}: ERROR - {str(e)}")
                )

        # Summary
        self.stdout.write("")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Total snapshots: {total}")
        self.stdout.write(f"Modified: {modified_count}")
        self.stdout.write(f"Errors: {error_count}")

        if dry_run:
            self.stdout.write(self.style.WARNING("(DRY RUN - no changes saved)"))
        else:
            self.stdout.write(self.style.SUCCESS("Normalization complete!"))

        if error_count > 0:
            raise CommandError(f"{error_count} snapshots had errors.")
