"""Report legacy EDIF liquidations that do not have migrated RH details."""

import csv
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)


def summarize_year_counts(rows):
    """Return ordered yearly totals from ``(year, has_rh)`` rows."""
    counts = defaultdict(lambda: {"liquidaciones_edif": 0, "sin_rh_migrado": 0})
    for year, has_rh in rows:
        counts[year]["liquidaciones_edif"] += 1
        if not has_rh:
            counts[year]["sin_rh_migrado"] += 1
    return [
        {"year": year, **counts[year]}
        for year in sorted(counts, key=lambda value: (value is None, value))
    ]


class Command(BaseCommand):
    help = "Reporta por anio las liquidaciones EDIF legacy sin detalle RH migrado. Solo lectura de BD."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-output",
            type=str,
            default=None,
            help="Ruta opcional para el CSV resumido.",
        )

    def handle(self, *args, **options):
        liquidaciones = (
            LiquidacionEdificacion.objects.filter(liquidacion__legacy=True)
            .annotate(
                rh_count=Count(
                    "liquidacion__liquidacion_delegados__detalles_honorario",
                    filter=Q(
                        liquidacion__liquidacion_delegados__detalles_honorario__recibo_mensual__isnull=True
                    ),
                )
            )
            .values_list("liquidacion__fecha_registro__year", "rh_count")
        )
        rows = summarize_year_counts((year, rh_count > 0) for year, rh_count in liquidaciones)

        self.stdout.write(self.style.SUCCESS("=== EDIF legacy RH gap report ==="))
        self.stdout.write("anio,liquidaciones_edif,sin_rh_migrado")
        for row in rows:
            self.stdout.write(
                f"{row['year']},{row['liquidaciones_edif']},{row['sin_rh_migrado']}"
            )

        if options["csv_output"]:
            output = Path(options["csv_output"])
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=["year", "liquidaciones_edif", "sin_rh_migrado"],
                )
                writer.writeheader()
                writer.writerows(rows)
            self.stdout.write(f"CSV: {output}")
