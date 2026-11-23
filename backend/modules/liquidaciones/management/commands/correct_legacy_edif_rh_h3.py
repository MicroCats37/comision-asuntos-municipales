"""Correct existing post-cutover EDIF RH details that were split by four."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)

from .legacy_edif import money, round_money
from .reconcile_legacy_edif_rh import (
    CUTOVER_DATE,
    H3_RATE,
    MONEY_TOLERANCE,
    classify_po,
    classify_rh,
)


RH_FIELDS = ("imp_bruto", "renta_cip", "aporte_codemu", "fondo_comun", "neto_honorario")


def distribute_bruto(subtotal, count: int = 3) -> list[Decimal]:
    """Split money exactly, assigning the rounding residue to the last details."""
    subtotal = money(subtotal)
    cents = int(subtotal * 100)
    base, residue = divmod(cents, count)
    return [Decimal(base + (index >= count - residue)) / 100 for index in range(count)]


def values_for_bruto(bruto: Decimal) -> dict[str, Decimal]:
    bruto = money(bruto)
    return {
        "imp_bruto": bruto,
        "renta_cip": round_money(bruto * Decimal("0.25")),
        "aporte_codemu": round_money(bruto * Decimal("0.05")),
        "fondo_comun": round_money(bruto * Decimal("0.10")),
        "neto_honorario": round_money(bruto * Decimal("0.60")),
    }


class Command(BaseCommand):
    help = "Retirado: no infiere RH EDIF desde subtotal/3 sin validar RH_EDIF."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Confirma la actualizacion transaccional.")
        parser.add_argument(
            "--allow-incomplete",
            action="store_true",
            help="Corrige detalles RH /4 aunque existan solo uno o dos; no crea filas faltantes.",
        )
        parser.add_argument("--fecha-desde", type=str, default=CUTOVER_DATE.isoformat())
        parser.add_argument("--csv-output", type=str, default=None)

    def handle(self, *args, **options):
        raise CommandError(
            "Unsafe correction disabled: validate each RH against RH_EDIF.csv with "
            "restore_legacy_edif_rh_h3 before changing amounts."
        )

        try:
            fecha_desde = date.fromisoformat(options["fecha_desde"])
        except ValueError as exc:
            raise CommandError("--fecha-desde must use YYYY-MM-DD") from exc

        candidates = list(
            LiquidacionEdificacion.objects.filter(
                liquidacion__legacy=True,
                liquidacion__fecha_registro__date__gte=fecha_desde,
                liquidacion__liquidacion_porcentaje_obra__porcentaje_liquidacion=H3_RATE,
            )
            .select_related("liquidacion", "liquidacion__liquidacion_porcentaje_obra")
            .order_by("numero")
        )
        rows = []
        targets = []
        skipped = 0
        for edificacion in candidates:
            liquidacion = edificacion.liquidacion
            details = list(
                DetalleHonorarioDelegado.objects.filter(
                    recibo_mensual__isnull=True,
                    liquidacion_delegado__liquidacion=liquidacion,
                ).order_by("liquidacion_delegado__especialidad_revision__nombre", "id")
            )
            rh_status, _ = classify_rh(details, liquidacion.sub_total, MONEY_TOLERANCE)
            if classify_po(liquidacion.liquidacion_porcentaje_obra) != "PO_CORRECTO" or rh_status != "RH_DIVIDIDO_4":
                continue
            if len(details) != 3 and not options["allow_incomplete"]:
                skipped += 1
                rows.append({"numero": edificacion.numero, "liquidacion_id": liquidacion.id, "status": "SKIPPED_UNSAFE_DETAIL_COUNT", "detail_count": len(details), "subtotal": money(liquidacion.sub_total)})
                continue
            allocations = (
                [values_for_bruto(value) for value in distribute_bruto(liquidacion.sub_total)]
                if len(details) == 3
                else [values_for_bruto(round_money(money(liquidacion.sub_total) / 3)) for _ in details]
            )
            targets.append((edificacion, details, allocations))
            for detail, values in zip(details, allocations):
                rows.append({"numero": edificacion.numero, "liquidacion_id": liquidacion.id, "detail_id": detail.id, "status": "PLANNED_INCOMPLETE" if len(details) != 3 else "PLANNED", "detail_count": len(details), "subtotal": money(liquidacion.sub_total), **{f"new_{field}": values[field] for field in RH_FIELDS}})

        if options["apply"]:
            with transaction.atomic():
                for edificacion, _, allocations in targets:
                    details = list(
                        DetalleHonorarioDelegado.objects.select_for_update()
                        .filter(recibo_mensual__isnull=True, liquidacion_delegado__liquidacion=edificacion.liquidacion)
                        .order_by("liquidacion_delegado__especialidad_revision__nombre", "id")
                    )
                    rh_status, _ = classify_rh(details, edificacion.liquidacion.sub_total, MONEY_TOLERANCE)
                    if (
                        rh_status != "RH_DIVIDIDO_4"
                        or (len(details) != 3 and not options["allow_incomplete"])
                    ):
                        raise CommandError(f"Candidate {edificacion.numero} changed after planning; transaction rolled back.")
                    for detail, values in zip(details, allocations):
                        for field, value in values.items():
                            setattr(detail, field, value)
                    DetalleHonorarioDelegado.objects.bulk_update(details, RH_FIELDS)

        if options["csv_output"]:
            output = Path(options["csv_output"])
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", newline="", encoding="utf-8") as handle:
                fieldnames = sorted({key for row in rows for key in row}) or ["numero", "status"]
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        mode = "APPLIED" if options["apply"] else "DRY_RUN"
        self.stdout.write(self.style.SUCCESS(f"=== EDIF RH H=3 correction ({mode}) ==="))
        self.stdout.write(f"Candidates corrected: {len(targets)}")
        self.stdout.write(f"Skipped unsafe:       {skipped}")
        self.stdout.write(
            "Details updated:      "
            + str(sum(len(details) for _, details, _ in targets) if options["apply"] else 0)
        )
        if options["csv_output"]:
            self.stdout.write(f"CSV:                  {options['csv_output']}")
