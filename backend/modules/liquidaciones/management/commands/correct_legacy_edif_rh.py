"""Correct existing legacy EDIF RH details from the persisted PO allocation."""

import csv
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)

from .legacy_edif import money, money_diff
from .reconcile_legacy_edif_rh import (
    CUTOVER_DATE,
    MONEY_TOLERANCE,
    RH_FIELDS,
    expected_bruto,
    expected_rh_values,
)


class Command(BaseCommand):
    help = "Correct existing post-cutover EDIF RH details. Dry-run by default."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--fecha-desde", default=CUTOVER_DATE.isoformat())
        parser.add_argument("--csv-output", required=True)

    def handle(self, *args, **options):
        try:
            fecha_desde = date.fromisoformat(options["fecha_desde"])
        except ValueError as exc:
            raise CommandError("--fecha-desde must use YYYY-MM-DD") from exc
        if fecha_desde < CUTOVER_DATE:
            raise CommandError(f"--fecha-desde must be on or after {CUTOVER_DATE}")

        edificaciones = (
            LiquidacionEdificacion.objects.filter(
                liquidacion__legacy=True,
                liquidacion__fecha_registro__date__gte=fecha_desde,
            )
            .select_related("liquidacion", "liquidacion__liquidacion_porcentaje_obra")
            .prefetch_related("liquidacion__liquidacion_porcentaje_obra__detalles")
            .order_by("numero")
        )
        targets = []
        rows = []
        for edificacion in edificaciones:
            liquidacion = edificacion.liquidacion
            po_details = list(liquidacion.liquidacion_porcentaje_obra.detalles.all())
            po_by_specialty = {detail.especialidad_id: detail for detail in po_details}
            rh_details = DetalleHonorarioDelegado.objects.filter(
                recibo_mensual__isnull=True,
                liquidacion_delegado__liquidacion=liquidacion,
            ).select_related("liquidacion_delegado__especialidad_revision")
            for rh_detail in rh_details:
                po_detail = po_by_specialty.get(
                    rh_detail.liquidacion_delegado.especialidad_revision_id
                )
                if po_detail is None:
                    continue
                expected = expected_rh_values(
                    expected_bruto(liquidacion, po_details, po_detail)
                )
                if all(
                    money_diff(getattr(rh_detail, field), expected[field])
                    <= MONEY_TOLERANCE
                    for field in RH_FIELDS
                ):
                    continue
                targets.append((rh_detail.id, expected))
                rows.append(
                    {
                        "numero": edificacion.numero,
                        "detail_id": str(rh_detail.id),
                        "especialidad": rh_detail.liquidacion_delegado.especialidad_revision.nombre,
                        "po_detail_subtotal": money(po_detail.subtotal),
                        "tarifa_aplicada": po_detail.tarifa_aplicada_id or "",
                        "porcentaje_aplicado": po_detail.porcentaje_aplicado or "",
                        "actual_imp_bruto": money(rh_detail.imp_bruto),
                        "expected_imp_bruto": expected["imp_bruto"],
                        "status": "APPLIED" if options["apply"] else "PLANNED",
                    }
                )

        if options["apply"]:
            with transaction.atomic():
                locked = {
                    detail.id: detail
                    for detail in DetalleHonorarioDelegado.objects.select_for_update(
                        of=("self",)
                    ).filter(id__in=[detail_id for detail_id, _ in targets])
                }
                for detail_id, expected in targets:
                    detail = locked[detail_id]
                    for field, value in expected.items():
                        setattr(detail, field, value)
                DetalleHonorarioDelegado.objects.bulk_update(
                    locked.values(), RH_FIELDS
                )

        output = Path(options["csv_output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else ["status"])
            writer.writeheader()
            writer.writerows(rows)
        self.stdout.write(self.style.SUCCESS(f"RH details {'corrected' if options['apply'] else 'planned'}: {len(targets)}"))
        self.stdout.write(f"CSV: {output}")
