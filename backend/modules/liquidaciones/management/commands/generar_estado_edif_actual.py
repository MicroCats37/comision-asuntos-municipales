"""Generate a current EDIF legacy status workbook from CSV IDs versus the database."""

import csv
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)


DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[4]
    / "core_application"
    / "seeds"
    / "historico"
    / "EDIF_ALL.csv"
)


def _text(value: str | None) -> str:
    return (value or "").strip()


def _decimal(value: str | None) -> Decimal | None:
    raw = _text(value)
    if not raw:
        return None
    raw = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _year(value: str | None) -> int | None:
    raw = _text(value)
    for format_string in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:10], format_string).year
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = "Genera el estado actual EDIF_ALL comparando ID legacy contra la base de datos."

    def add_arguments(self, parser):
        parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
        parser.add_argument("--output-path", type=Path, default=None)

    def handle(self, *args, **options):
        data_path = options["data_path"]
        if not data_path.exists():
            self.stderr.write(self.style.ERROR(f"No existe el CSV: {data_path}"))
            return

        existing_ids = {
            str(numero)
            for numero in LiquidacionEdificacion.objects.values_list("numero", flat=True)
        }
        rows_by_status = {"EXISTENTE": [], "PENDIENTE": []}
        summary = defaultdict(
            lambda: {"EXISTENTE": [0, Decimal("0"), Decimal("0")], "PENDIENTE": [0, Decimal("0"), Decimal("0")]}
        )

        with data_path.open("r", encoding="utf-8-sig", newline="") as source:
            for csv_row, row in enumerate(csv.DictReader(source, delimiter=";"), start=2):
                edif_id = _text(row.get("ID"))
                status = "EXISTENTE" if edif_id in existing_ids else "PENDIENTE"
                fecha = _text(row.get("FECHA"))
                subtotal = _decimal(row.get("SUBTOTAL"))
                total = _decimal(row.get("TOTAL"))
                year = _year(fecha)
                output_row = [
                    csv_row,
                    edif_id,
                    _text(row.get("NRO")),
                    fecha,
                    year,
                    status,
                    _text(row.get("NROEXPDTE")),
                    _text(row.get("ESPECIALIDAD")),
                    _text(row.get("RAZONSOCIAL")),
                    _text(row.get("PROYECTO")),
                    _decimal(row.get("VALOROBRA")),
                    subtotal,
                    total,
                ]
                rows_by_status[status].append(output_row)
                bucket = summary[year]
                bucket[status][0] += 1
                bucket[status][1] += subtotal or Decimal("0")
                bucket[status][2] += total or Decimal("0")

        output_path = options["output_path"]
        if output_path is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(__file__).resolve().parents[5] / "result" / "EDIF" / f"EDIF_ALL_estado_actual_{run_id}.xlsx"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        workbook = Workbook()
        summary_sheet = workbook.active
        summary_sheet.title = "Resumen por año"
        headers = [
            "Año", "Existentes", "Pendientes", "Subtotal existente", "Subtotal pendiente",
            "Total existente", "Total pendiente",
        ]
        summary_sheet.append(headers)
        for year in sorted(summary, key=lambda value: value if value is not None else 0):
            existing_count, existing_subtotal, existing_total = summary[year]["EXISTENTE"]
            pending_count, pending_subtotal, pending_total = summary[year]["PENDIENTE"]
            summary_sheet.append([
                year, existing_count, pending_count, existing_subtotal, pending_subtotal,
                existing_total, pending_total,
            ])

        data_headers = [
            "Fila CSV", "ID EDIF", "NRO", "Fecha", "Año", "Estado actual", "Expediente",
            "Especialidad", "Razón social", "Proyecto", "Valor obra", "Subtotal legacy", "Total legacy",
        ]
        for status, sheet_name in (("EXISTENTE", "Padres existentes"), ("PENDIENTE", "Padres pendientes")):
            sheet = workbook.create_sheet(sheet_name)
            sheet.append(data_headers)
            for row in rows_by_status[status]:
                sheet.append(row)

        header_fill = PatternFill("solid", fgColor="1F4E78")
        header_font = Font(color="FFFFFF", bold=True)
        for sheet in workbook.worksheets:
            for cell in sheet[1]:
                cell.fill = header_fill
                cell.font = header_font
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in range(1, sheet.max_column + 1):
                sheet.column_dimensions[get_column_letter(column)].width = min(
                    max(12, max(len(str(cell.value or "")) for cell in sheet[get_column_letter(column)]) + 2), 42
                )
            for row in sheet.iter_rows(min_row=2):
                for cell in row:
                    if isinstance(cell.value, Decimal):
                        cell.number_format = "#,##0.00"

        workbook.save(output_path)
        self.stdout.write(self.style.SUCCESS(
            f"Reporte generado: {output_path}\n"
            f"Existentes: {len(rows_by_status['EXISTENTE']):,}\n"
            f"Pendientes: {len(rows_by_status['PENDIENTE']):,}"
        ))
