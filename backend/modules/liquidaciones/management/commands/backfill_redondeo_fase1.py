"""
Backfill Phase 1: populate new high-precision rounding fields in LiquidacionPorcentajeObraDetalle.

Schema migration is blocked by environment (makemigrations unavailable), but the
model fields already exist (importe_parcial, ajuste_redondeo).
This command performs a data-only backfill:

  - LiquidacionPorcentajeObraDetalle:
      importe_parcial = subtotal   (theoretical value, no rounding needed since subtotal is already rounded)
      ajuste_redondeo = 0.00      (no remainder correction needed for backfill — subtotal is exact)

  - DetalleHonorarioDelegado & ReciboHonorarioDelegadoMensual:
      Print a WARNING that these models also have the new fields but their
      calculation logic is owned by the finanzas module. Manual review required.

Idempotent: only updates rows where the new fields are NULL.

Usage:
    python manage.py backfill_redondeo_fase1 --settings=config.settings.development
    python manage.py backfill_redondeo_fase1 --dry-run --settings=config.settings.development
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObraDetalle,
)


class Command(BaseCommand):
    help = "Backfill importe_parcial / ajuste_redondeo in LiquidacionPorcentajeObraDetalle."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate without writing to the database.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for bulk_update (default: 500).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        self.stdout.write(self.style.NOTICE("=== Phase 1: Backfill LiquidacionPorcentajeObraDetalle ==="))

        # --- LiquidacionPorcentajeObraDetalle ---
        detalle_qs = LiquidacionPorcentajeObraDetalle.objects.filter(
            importe_parcial__isnull=True,
        )

        total_to_update = detalle_qs.count()
        if total_to_update == 0:
            self.stdout.write(self.style.SUCCESS("No LiquidacionPorcentajeObraDetalle rows with NULL importe_parcial."))
        else:
            self.stdout.write(f"Found {total_to_update} LiquidacionPorcentajeObraDetalle rows to backfill.")
            updated = 0

            if dry_run:
                sample = detalle_qs[:3]
                for d in sample:
                    self.stdout.write(
                        f"  [DRY-RUN] would set pk={d.pk}: "
                        f"importe_parcial={d.subtotal}, ajuste_redondeo=0.00"
                    )
                if total_to_update > 3:
                    self.stdout.write(f"  ... and {total_to_update - 3} more.")
            else:
                # Process in batches to avoid memory issues
                detalle_ids = list(detalle_qs.values_list("pk", flat=True))
                for i in range(0, len(detalle_ids), batch_size):
                    batch_ids = detalle_ids[i:i + batch_size]
                    batch_qs = LiquidacionPorcentajeObraDetalle.objects.filter(pk__in=batch_ids)
                    batch_updates = []
                    for d in batch_qs:
                        d.importe_parcial = d.subtotal
                        d.ajuste_redondeo = Decimal("0.00")
                        batch_updates.append(d)
                    LiquidacionPorcentajeObraDetalle.objects.bulk_update(
                        batch_updates,
                        ["importe_parcial", "ajuste_redondeo"],
                    )
                    updated += len(batch_updates)
                    self.stdout.write(f"  Updated {updated}/{total_to_update} ...")

            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f"LiquidacionPorcentajeObraDetalle: {updated} rows updated.")
                )

        # --- DetalleHonorarioDelegado ---
        self._warn_placeholder(
            model_name="DetalleHonorarioDelegado",
            note=(
                "This model has importe_parcial, ajuste_redondeo fields. "
                "Its calculation logic lives in the finanzas module. "
                "Manual review / finanzas team required."
            ),
            dry_run=dry_run,
        )

        # --- ReciboHonorarioDelegadoMensual ---
        self._warn_placeholder(
            model_name="ReciboHonorarioDelegadoMensual",
            note=(
                "This model has importe_parcial, ajuste_redondeo fields. "
                "Its calculation logic lives in the finanzas module. "
                "Manual review / finanzas team required."
            ),
            dry_run=dry_run,
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: No changes were written to the database."))

    def _warn_placeholder(self, model_name: str, note: str, dry_run: bool):
        """Print a warning that this model's fields need manual review."""
        self.stdout.write(self.style.WARNING(f"\n⚠️  {model_name}: manual review required"))
        self.stdout.write(f"    {note}")
        if dry_run:
            self.stdout.write(f"    [DRY-RUN] No action taken.")
