"""Restore incorrectly broadened EDIF RH H=3 corrections from RH_EDIF.csv."""

import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)


RH_FIELDS = ("imp_bruto", "renta_cip", "aporte_codemu", "fondo_comun", "neto_honorario")
SOURCE_FIELDS = {
    "imp_bruto": "IMPBRUTO",
    "renta_cip": "RENTACIP",
    "aporte_codemu": "APORCODEMU",
    "fondo_comun": "FONDOCOMUN",
    "neto_honorario": "NETOHONORA",
}
ROOT = Path(__file__).resolve().parents[5]
DEFAULT_RH_CSV = ROOT / "RH_EDIF.csv"
DEFAULT_APPLIED_REPORTS = (
    ROOT / "result" / "EDIF" / "rh_h3_correction_applied.csv",
    ROOT / "result" / "EDIF" / "rh_h3_incomplete_correction_applied.csv",
)


def normalize_cip(value) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return digits.lstrip("0") or "0"


def normalize_order(value) -> str:
    return str(value or "").strip()


def parse_decimal(value) -> Decimal | None:
    raw = str(value or "").strip()
    if not raw or raw.upper() in {"NULL", "NONE"}:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def applied_detail_ids(report_paths: tuple[Path, ...]) -> set[str]:
    detail_ids = set()
    for path in report_paths:
        with path.open(newline="", encoding="utf-8") as report:
            for row in csv.DictReader(report):
                if row.get("status", "").startswith("PLANNED") and row.get("detail_id"):
                    detail_ids.add(row["detail_id"])
    return detail_ids


def source_by_key(path: Path) -> tuple[dict[tuple[int, str, str], dict[str, Decimal]], set[tuple[int, str, str]]]:
    rows_by_key = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source, delimiter=";"):
            try:
                numero = int(str(row.get("NRO", "")).strip())
            except ValueError:
                continue
            key = (numero, normalize_cip(row.get("CIP")), normalize_order(row.get("NROORDEN")))
            values = {field: parse_decimal(row.get(column)) for field, column in SOURCE_FIELDS.items()}
            if not key[1] or not key[2] or any(value is None for value in values.values()):
                continue
            rows_by_key[key].append(values)

    source = {}
    ambiguous = set()
    for key, values in rows_by_key.items():
        unique_values = {tuple(item[field] for field in RH_FIELDS) for item in values}
        if len(unique_values) == 1:
            source[key] = values[0]
        else:
            ambiguous.add(key)
    return source, ambiguous


def po_category(porcentaje) -> str:
    if porcentaje.estrategia_cotizacion == "TOTAL_EXPLICITO_SELECCIONADAS":
        # Importe autoritativo repartido entre las SELECCIONADAS: el detalle
        # conserva el importe completo (no es un reparto por H habilitadas).
        return "TOTAL_EXPLICITO_SELECCIONADAS"
    if porcentaje.estrategia_cotizacion == "TOTAL_EXPLICITO":
        return "TOTAL_EXPLICITO"
    if porcentaje.porcentaje_tarifa == Decimal("0.0005"):
        if porcentaje.cantidad_especialidades_habilitadas == 1:
            return "SINGLE_SPECIALTY_UNIT_RATE"
        return "UNIT_RATE_FRACTIONAL"
    return "OTHER_PO_STRATEGY"


class Command(BaseCommand):
    help = "Restaura solo RH afectados por las correcciones H=3 desde RH_EDIF.csv. Dry-run por defecto."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Confirma la restauracion transaccional.")
        parser.add_argument("--rh-csv", type=str, default=str(DEFAULT_RH_CSV))
        parser.add_argument(
            "--applied-report",
            action="append",
            dest="applied_reports",
            help="Reporte aplicado a auditar; se puede repetir. Por defecto usa ambos reportes H=3 aplicados.",
        )
        parser.add_argument("--csv-output", type=str, required=True)

    def handle(self, *args, **options):
        rh_path = Path(options["rh_csv"])
        report_paths = tuple(Path(path) for path in (options["applied_reports"] or DEFAULT_APPLIED_REPORTS))
        missing = [str(path) for path in (rh_path, *report_paths) if not path.exists()]
        if missing:
            raise CommandError("Required audit input does not exist: " + ", ".join(missing))

        detail_ids = applied_detail_ids(report_paths)
        source, ambiguous_source = source_by_key(rh_path)
        details = list(
            DetalleHonorarioDelegado.objects.filter(id__in=detail_ids)
            .select_related(
                "liquidacion_delegado__liquidacion__edificaciones",
                "liquidacion_delegado__liquidacion__liquidacion_porcentaje_obra",
                "liquidacion_delegado__delegado__perfil_ingeniero",
            )
            .order_by("id")
        )
        found_ids = {str(detail.id) for detail in details}
        history_model = DetalleHonorarioDelegado.history.model
        # The previous bulk_update did not create history. Count it only as evidence in the report.
        history_ids = set(history_model.objects.filter(id__in=detail_ids).values_list("id", flat=True))
        rows = []
        targets = []
        for detail in details:
            liquidacion = detail.liquidacion_delegado.liquidacion
            edificacion = liquidacion.edificaciones
            key = (
                edificacion.numero,
                normalize_cip(detail.liquidacion_delegado.delegado.perfil_ingeniero.cip),
                normalize_order(detail.liquidacion_delegado.numero_rh),
            )
            row = {
                "detail_id": str(detail.id),
                "numero": edificacion.numero,
                "cip": key[1],
                "nro_orden": key[2],
                "po_category": po_category(liquidacion.liquidacion_porcentaje_obra),
                "estrategia_cotizacion": liquidacion.liquidacion_porcentaje_obra.estrategia_cotizacion,
                "porcentaje_tarifa": liquidacion.liquidacion_porcentaje_obra.porcentaje_tarifa,
                "cantidad_habilitadas": liquidacion.liquidacion_porcentaje_obra.cantidad_especialidades_habilitadas,
                "history_available": str(detail.id) in history_ids,
            }
            for field in RH_FIELDS:
                row[f"current_{field}"] = getattr(detail, field)

            if key in ambiguous_source:
                row["status"] = "SKIPPED_AMBIGUOUS_SOURCE"
            elif key not in source:
                row["status"] = "SKIPPED_SOURCE_NOT_FOUND"
            else:
                values = source[key]
                for field, value in values.items():
                    row[f"source_{field}"] = value
                if all(getattr(detail, field) == values[field] for field in RH_FIELDS):
                    row["status"] = "RETAINED_SOURCE_MATCH"
                else:
                    row["status"] = "RESTORE_FROM_SOURCE"
                    targets.append((detail, values, tuple(getattr(detail, field) for field in RH_FIELDS)))
            rows.append(row)

        for missing_id in sorted(detail_ids - found_ids):
            rows.append({"detail_id": missing_id, "status": "SKIPPED_DETAIL_NOT_FOUND"})

        if options["apply"]:
            with transaction.atomic():
                for detail, values, previous in targets:
                    locked = DetalleHonorarioDelegado.objects.select_for_update().get(id=detail.id)
                    if tuple(getattr(locked, field) for field in RH_FIELDS) != previous:
                        raise CommandError(f"Detail {locked.id} changed after audit; transaction rolled back.")
                    for field, value in values.items():
                        setattr(locked, field, value)
                    locked.save(update_fields=RH_FIELDS)

        output = Path(options["csv_output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = sorted({key for row in rows for key in row}) or ["detail_id", "status"]
        with output.open("w", newline="", encoding="utf-8") as report:
            writer = csv.DictWriter(report, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        counts = defaultdict(int)
        category_counts = defaultdict(int)
        for row in rows:
            counts[row["status"]] += 1
            if row.get("po_category"):
                category_counts[row["po_category"]] += 1
        mode = "APPLIED" if options["apply"] else "DRY_RUN"
        self.stdout.write(self.style.SUCCESS(f"=== EDIF RH H=3 restoration ({mode}) ==="))
        self.stdout.write(f"Reported affected details: {len(detail_ids)}")
        self.stdout.write(f"Details found:            {len(details)}")
        self.stdout.write(f"Restored from source:     {len(targets) if options['apply'] else 0}")
        for status, count in sorted(counts.items()):
            self.stdout.write(f"{status}: {count}")
        for category, count in sorted(category_counts.items()):
            self.stdout.write(f"PO {category}: {count}")
        self.stdout.write(f"CSV: {output}")
