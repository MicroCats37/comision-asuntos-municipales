"""Explain legacy EDIF RH gaps using the authoritative RH_EDIF source."""

import csv
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)

from .import_rh_delegados_historicos import (
    DEFAULT_RH_CSV,
    Command as ImportCommand,
    build_especialidad_index,
    parse_int,
    read_rh_rows,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


def gap_cause(valid_by_nro, invalid_by_nro, omitted_by_nro, numero):
    if numero not in valid_by_nro and numero not in invalid_by_nro:
        return "SOURCE_ABSENT"
    if numero not in valid_by_nro:
        return "SOURCE_MALFORMED"
    reasons = omitted_by_nro.get(numero, [])
    return "SOURCE_EXCLUDED:" + "+".join(sorted(set(reasons))) if reasons else "SOURCE_MATCHED_NOT_MIGRATED"


class Command(BaseCommand):
    help = "Explica las brechas RH EDIF por fuente ausente, malformada, no emparejable o excluida."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=2026)
        parser.add_argument("--rh-csv", type=str, default=str(DEFAULT_RH_CSV))
        parser.add_argument("--csv-output", type=str, default=None)

    def handle(self, *args, **options):
        valid, invalid = read_rh_rows(Path(options["rh_csv"]))
        valid_by_nro = defaultdict(list)
        invalid_by_nro = defaultdict(list)
        for row in valid:
            valid_by_nro[row.nro].append(row)
        for row in invalid:
            numero = parse_int(row["nro"])
            if numero is not None:
                invalid_by_nro[numero].append(row)

        planner = ImportCommand()
        indexes = planner._cargar_indexes(valid)
        _, _, omitted, _ = planner._planificar(
            valid, indexes, build_especialidad_index(EspecialidadRevision.objects.all())
        )
        omitted_by_nro = defaultdict(list)
        for row in omitted:
            omitted_by_nro[row["nro"]].append(row["motivo"])

        parent_numbers = set(
            LiquidacionEdificacion.objects.filter(liquidacion__legacy=True).values_list("numero", flat=True)
        )
        source_numbers = set(valid_by_nro) | set(invalid_by_nro)
        missing_parent_source_rows = sum(
            len(valid_by_nro.get(numero, [])) + len(invalid_by_nro.get(numero, []))
            for numero in source_numbers - parent_numbers
        )
        gaps = (
            LiquidacionEdificacion.objects.filter(
                liquidacion__legacy=True,
                liquidacion__fecha_registro__year=options["year"],
            )
            .annotate(rh_count=Count("liquidacion__liquidacion_delegados__detalles_honorario", filter=Q(liquidacion__liquidacion_delegados__detalles_honorario__recibo_mensual__isnull=True)))
            .filter(rh_count=0)
            .select_related("liquidacion")
            .order_by("numero")
        )
        rows = []
        causes = Counter()
        for edif in gaps:
            cause = gap_cause(valid_by_nro, invalid_by_nro, omitted_by_nro, edif.numero)
            causes[cause] += 1
            rows.append({"numero": edif.numero, "liquidacion_id": edif.liquidacion_id, "fecha_registro": edif.liquidacion.fecha_registro.date(), "cause": cause, "valid_source_rows": len(valid_by_nro.get(edif.numero, [])), "invalid_source_rows": len(invalid_by_nro.get(edif.numero, []))})

        self.stdout.write(self.style.SUCCESS(f"=== EDIF RH gaps {options['year']} ==="))
        self.stdout.write(f"Missing RH parents:                 {len(rows)}")
        self.stdout.write(f"RH source rows without EDIF parent: {missing_parent_source_rows}")
        for cause in ("SOURCE_ABSENT", "SOURCE_MALFORMED", "SOURCE_MATCHED_NOT_MIGRATED"):
            self.stdout.write(f"{cause}: {causes[cause]}")
        for cause, count in sorted(causes.items()):
            if cause.startswith("SOURCE_EXCLUDED:"):
                self.stdout.write(f"{cause}: {count}")
        if options["csv_output"]:
            output = Path(options["csv_output"])
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["numero", "liquidacion_id", "fecha_registro", "cause", "valid_source_rows", "invalid_source_rows"])
                writer.writeheader()
                writer.writerows(rows)
            self.stdout.write(f"CSV: {output}")
