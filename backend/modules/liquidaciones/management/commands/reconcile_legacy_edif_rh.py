"""Read-only reconciliation of post-cutover EDIF RH against persisted PO details."""

import csv
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from .legacy_edif import money, money_diff, round_money


CUTOVER_DATE = date(2026, 5, 1)
MONEY_TOLERANCE = Decimal("0.01")
RH_FIELDS = ("imp_bruto", "renta_cip", "aporte_codemu", "fondo_comun", "neto_honorario")


def expected_rh_values(po_detail_subtotal) -> dict[str, Decimal]:
    """Derive RH components from the persisted PO allocation for one specialty."""
    bruto = money(po_detail_subtotal)
    return {
        "imp_bruto": bruto,
        "renta_cip": round_money(bruto * Decimal("0.25")),
        "aporte_codemu": round_money(bruto * Decimal("0.05")),
        "fondo_comun": round_money(bruto * Decimal("0.10")),
        "neto_honorario": round_money(bruto * Decimal("0.60")),
    }


def expected_bruto(liquidacion, po_details, po_detail) -> Decimal:
    """Resolve RH from the applied tariff first, then the persisted PO detail."""
    if (
        len(po_details) == 1
        and po_detail.tarifa_aplicada_id
        and po_detail.porcentaje_aplicado == Decimal("0.0005")
    ):
        return money(liquidacion.sub_total)
    return money(po_detail.subtotal)


def po_allocation_classification(porcentaje, detail_count: int) -> str:
    if porcentaje.estrategia_cotizacion == "TOTAL_EXPLICITO_SELECCIONADAS":
        # El importe autoritativo se reparte entre las SELECCIONADAS (no entre H
        # habilitadas): el detalle conserva el importe completo.
        return "PO_TOTAL_EXPLICITO_SELECCIONADAS_POR_DETALLE"
    if porcentaje.estrategia_cotizacion == "TOTAL_EXPLICITO":
        return "PO_TOTAL_EXPLICITO_POR_DETALLE"
    if detail_count == 1:
        return "PO_EXCLUSIVO_ESPECIALIDAD"
    if detail_count == 3:
        return "PO_TRES_DETALLES_PERSISTIDOS"
    return "PO_POR_DETALLE_PERSISTIDO"


def rh_classification(
    detail, expected: dict[str, Decimal] | None, tolerance: Decimal
) -> str:
    if expected is None:
        return "RH_SIN_PO_DETALLE"
    if all(
        money_diff(getattr(detail, field), expected[field]) <= tolerance
        for field in RH_FIELDS
    ):
        return "RH_CORRECTO"
    return "RH_DISCREPANTE_PO_DETALLE"


def summarize_parent_counts(parent_records: list[dict], rows: list[dict]) -> dict[str, int]:
    """Summarize reconciliation outcomes by unique EDIF parent ``numero``."""
    parent_numbers = {record["numero"] for record in parent_records}
    parents_with_rh = {
        record["numero"] for record in parent_records if record["has_rh"]
    }
    parents_with_existing_mismatches = {
        row["numero"]
        for row in rows
        if row["rh_classification"].startswith("RH_DISCREPANTE_PO_DETALLE")
    }
    parents_with_missing_po_to_rh = {
        row["numero"]
        for row in rows
        if row["rh_classification"] == "RH_FALTANTE_PARA_PO_DETALLE"
    }
    return {
        "legacy_edif_post_cutover_parents": len(parent_numbers),
        "parents_with_any_rh": len(parents_with_rh),
        "parents_without_rh": len(parent_numbers - parents_with_rh),
        "parents_with_existing_rh_mismatches": len(parents_with_existing_mismatches),
        "parents_with_missing_po_to_rh_specialties": len(
            parents_with_missing_po_to_rh
        ),
    }


def h3_existing_mismatch_parents(rows: list[dict]) -> list[dict]:
    """Return one representative row per H3 parent with an existing RH mismatch."""
    parents = {}
    for row in rows:
        if (
            row["po_detail_count"] == 3
            and row["rh_classification"].startswith("RH_DISCREPANTE_PO_DETALLE")
        ):
            parents.setdefault(row["numero"], row)
    return [parents[numero] for numero in sorted(parents)]


def build_reconciliation_rows(
    liquidacion, porcentaje, rh_details, tolerance: Decimal
) -> list[dict]:
    """Reconcile RH rows by specialty; RH cardinality never changes a PO allocation."""
    po_details = list(porcentaje.detalles.all())
    po_by_specialty = {detail.especialidad_id: detail for detail in po_details}
    rh_by_specialty = defaultdict(list)
    for rh_detail in rh_details:
        rh_by_specialty[rh_detail.liquidacion_delegado.especialidad_revision_id].append(
            rh_detail
        )

    po_classification = po_allocation_classification(porcentaje, len(po_details))
    rows = []
    all_specialties = sorted(set(po_by_specialty) | set(rh_by_specialty), key=str)
    for specialty_id in all_specialties:
        po_detail = po_by_specialty.get(specialty_id)
        rh_for_specialty = rh_by_specialty.get(specialty_id, [])
        expected = (
            expected_rh_values(expected_bruto(liquidacion, po_details, po_detail))
            if po_detail
            else None
        )
        specialty_name = (
            po_detail.especialidad.nombre
            if po_detail
            else rh_for_specialty[0].liquidacion_delegado.especialidad_revision.nombre
        )
        base = {
            "numero": liquidacion.edificaciones.numero,
            "liquidacion_id": str(liquidacion.id),
            "expediente": liquidacion.expediente or "",
            "fecha_registro": liquidacion.fecha_registro.date().isoformat(),
            "especialidad_id": str(specialty_id),
            "especialidad": specialty_name,
            "estrategia_cotizacion": porcentaje.estrategia_cotizacion,
            "cantidad_habilitadas": porcentaje.cantidad_especialidades_habilitadas
            or "",
            "po_detail_id": str(po_detail.id) if po_detail else "",
            "po_detail_subtotal": str(money(po_detail.subtotal)) if po_detail else "",
            "po_detail_count": len(po_details),
            "po_classification": po_classification,
            **{
                f"expected_{field}": str(expected[field]) if expected else ""
                for field in RH_FIELDS
            },
        }
        if not rh_for_specialty:
            rows.append(
                {
                    **base,
                    "rh_detail_id": "",
                    "rh_count_specialty": 0,
                    "rh_classification": "RH_FALTANTE_PARA_PO_DETALLE",
                    "classification": f"{po_classification}+RH_FALTANTE_PARA_PO_DETALLE",
                    **{f"actual_{field}": "" for field in RH_FIELDS},
                }
            )
            continue

        for rh_detail in rh_for_specialty:
            rh_status = rh_classification(rh_detail, expected, tolerance)
            if len(rh_for_specialty) > 1:
                rh_status = f"{rh_status}_DUPLICADO_ESPECIALIDAD"
            rows.append(
                {
                    **base,
                    "rh_detail_id": str(rh_detail.id),
                    "rh_count_specialty": len(rh_for_specialty),
                    "rh_classification": rh_status,
                    "classification": f"{po_classification}+{rh_status}",
                    **{
                        f"actual_{field}": str(money(getattr(rh_detail, field)))
                        for field in RH_FIELDS
                    },
                }
            )
    return rows


class Command(BaseCommand):
    help = "Conciliación EDIF RH de solo lectura contra detalles PO persistidos desde el corte."

    def add_arguments(self, parser):
        parser.add_argument("--numero", type=int, default=None)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--fecha-desde", type=str, default=CUTOVER_DATE.isoformat())
        parser.add_argument("--tolerance", type=str, default=str(MONEY_TOLERANCE))
        parser.add_argument("--csv-output", type=str, required=True)
        parser.add_argument("--summary-output", type=str, default=None)
        parser.add_argument("--h3-mismatches-output", type=str, default=None)
        parser.add_argument("--only-mismatches", action="store_true")

    def handle(self, *args, **options):
        try:
            fecha_desde = date.fromisoformat(options["fecha_desde"])
        except ValueError as exc:
            raise CommandError("--fecha-desde must use YYYY-MM-DD") from exc
        if fecha_desde < CUTOVER_DATE:
            raise CommandError(
                f"--fecha-desde must be on or after {CUTOVER_DATE.isoformat()}"
            )
        tolerance = money(options["tolerance"])
        if tolerance < 0:
            raise CommandError("--tolerance must be >= 0")
        if options["limit"] is not None and options["limit"] < 1:
            raise CommandError("--limit must be >= 1")

        rh_prefetch = Prefetch(
            "liquidacion__liquidacion_delegados__detalles_honorario",
            queryset=DetalleHonorarioDelegado.objects.filter(
                recibo_mensual__isnull=True
            ).select_related("liquidacion_delegado__especialidad_revision"),
            to_attr="reconciliation_rh_details",
        )
        qs = (
            LiquidacionEdificacion.objects.filter(
                liquidacion__legacy=True,
                liquidacion__fecha_registro__date__gte=fecha_desde,
            )
            .select_related("liquidacion", "liquidacion__liquidacion_porcentaje_obra")
            .prefetch_related(
                rh_prefetch,
                "liquidacion__liquidacion_porcentaje_obra__detalles__especialidad",
            )
            .order_by("numero")
        )
        if options["numero"] is not None:
            qs = qs.filter(numero=options["numero"])
        if options["limit"] is not None:
            qs = qs[: options["limit"]]

        rows = []
        parent_records = []
        for edificacion in qs:
            liquidacion = edificacion.liquidacion
            porcentaje = liquidacion.liquidacion_porcentaje_obra
            rh_details = [
                detail
                for delegado in liquidacion.liquidacion_delegados.all()
                for detail in getattr(delegado, "reconciliation_rh_details", [])
            ]
            parent_records.append(
                {"numero": edificacion.numero, "has_rh": bool(rh_details)}
            )
            rows.extend(
                build_reconciliation_rows(
                    liquidacion, porcentaje, rh_details, tolerance
                )
            )

        output = Path(options["csv_output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self._fieldnames())
            writer.writeheader()
            writer.writerows(rows)

        existing_mismatches = [
            row
            for row in rows
            if row["rh_classification"].startswith("RH_DISCREPANTE_PO_DETALLE")
        ]
        missing_po_to_rh = [
            row
            for row in rows
            if row["rh_classification"] == "RH_FALTANTE_PARA_PO_DETALLE"
        ]
        mismatches = existing_mismatches + missing_po_to_rh
        parent_counts = summarize_parent_counts(parent_records, rows)
        h3_parents = h3_existing_mismatch_parents(rows)
        display_rows = mismatches if options["only_mismatches"] else rows
        for row in display_rows[:10]:
            self.stdout.write(
                f"{row['classification']} numero={row['numero']} especialidad={row['especialidad']} "
                f"esperado={row['expected_imp_bruto']} actual={row['actual_imp_bruto']}"
            )
        counts = Counter(row["classification"] for row in rows)
        h3_output = (
            Path(options["h3_mismatches_output"])
            if options["h3_mismatches_output"]
            else output.with_name(f"{output.stem}_h3_existing_rh_mismatches.csv")
        )
        h3_output.parent.mkdir(parents=True, exist_ok=True)
        with h3_output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self._fieldnames())
            writer.writeheader()
            writer.writerows(h3_parents)
        summary_output = (
            Path(options["summary_output"])
            if options["summary_output"]
            else output.with_suffix(".md")
        )
        self._write_summary(
            summary_output,
            fecha_desde,
            output,
            h3_output,
            rows,
            mismatches,
            counts,
            parent_counts,
            h3_parents,
        )
        self.stdout.write(
            self.style.SUCCESS("=== EDIF RH reconciliation (read-only) ===")
        )
        self.stdout.write(f"Fecha desde:             {fecha_desde.isoformat()}")
        self.stdout.write(f"Filas conciliadas:       {len(rows)}")
        self.stdout.write(f"Filas RH existentes discrepantes: {len(existing_mismatches)}")
        self.stdout.write(f"Lineas PO sin RH:        {len(missing_po_to_rh)}")
        self.stdout.write("Padres unicos:")
        for key, count in parent_counts.items():
            self.stdout.write(f"  {key}: {count}")
        self.stdout.write(f"Padres H3 con RH existente discrepante: {len(h3_parents)}")
        for classification, count in sorted(counts.items()):
            self.stdout.write(f"{classification}: {count}")
        self.stdout.write(f"CSV:                     {output}")
        self.stdout.write(f"CSV H3:                  {h3_output}")
        self.stdout.write(f"Resumen:                 {summary_output}")

    @staticmethod
    def _write_summary(
        summary_output,
        fecha_desde,
        csv_output,
        h3_output,
        rows,
        mismatches,
        counts,
        parent_counts,
        h3_parents,
    ):
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        with summary_output.open("w", encoding="utf-8") as report:
            report.write("# EDIF RH reconciliation\n\n")
            report.write(
                "Read-only reconciliation against persisted PO details by specialty.\n\n"
            )
            report.write(f"- Cutover scope: `{fecha_desde.isoformat()}` onward\n")
            report.write(f"- Detail CSV: `{csv_output.name}`\n")
            report.write(f"- H3 existing-RH mismatch CSV: `{h3_output.name}`\n")
            report.write(f"- Reconciled rows: {len(rows)}\n")
            report.write(f"- Existing RH discrepancy lines: {sum(1 for row in mismatches if row['rh_classification'].startswith('RH_DISCREPANTE_PO_DETALLE'))}\n")
            report.write(f"- Missing PO-to-RH specialty lines: {sum(1 for row in mismatches if row['rh_classification'] == 'RH_FALTANTE_PARA_PO_DETALLE')}\n\n")
            report.write("## Unique parent records\n\n")
            for key, count in parent_counts.items():
                report.write(f"- `{key}`: {count}\n")
            report.write(
                f"- `h3_parents_with_existing_rh_mismatches`: {len(h3_parents)}\n\n"
            )
            report.write("## Counts by classification\n\n")
            for classification, count in sorted(counts.items()):
                report.write(f"- `{classification}`: {count}\n")
            report.write("\n## Discrepancy examples\n\n")
            report.write(
                "| Numero | Specialty | PO classification | RH classification | Expected bruto | Actual bruto |\n"
            )
            report.write("| --- | --- | --- | --- | ---: | ---: |\n")
            for row in mismatches[:10]:
                report.write(
                    f"| {row['numero']} | {row['especialidad']} | {row['po_classification']} | "
                    f"{row['rh_classification']} | {row['expected_imp_bruto']} | "
                    f"{row['actual_imp_bruto']} |\n"
                )

    @staticmethod
    def _fieldnames():
        return [
            "numero",
            "liquidacion_id",
            "expediente",
            "fecha_registro",
            "especialidad_id",
            "especialidad",
            "estrategia_cotizacion",
            "cantidad_habilitadas",
            "po_detail_id",
            "po_detail_subtotal",
            "po_detail_count",
            "po_classification",
            "rh_detail_id",
            "rh_count_specialty",
            "rh_classification",
            "classification",
            *[f"expected_{field}" for field in RH_FIELDS],
            *[f"actual_{field}" for field in RH_FIELDS],
        ]
