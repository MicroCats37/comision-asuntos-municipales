"""Safely curate expediente and active comprobante fields for imported legacy IO."""

import csv
import re
import zipfile
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.liquidaciones.models import LiquidacionComprobante, LiquidacionInspeccionObra


DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[4]
    / "core_application"
    / "seeds"
    / "historico"
    / "IO_ALL.csv"
)


def _blank(value):
    return value is None or str(value).strip().upper() in {"", "NULL"}


def _parse_date(value):
    if _blank(value) or re.match(r"^1/\d{2}/1900", str(value).strip()):
        return None
    for format_string in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value).strip(), format_string).date()
        except ValueError:
            continue
    raise ValueError(f"invalid receipt date: {value!r}")


def _parse_decimal(value):
    if _blank(value):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid total: {value!r}") from exc


def _parse_invoice(value):
    if _blank(value):
        return None, None, None
    raw = str(value).strip()
    serie, numero = (raw.split("-", 1) + [None])[:2] if "-" in raw else (None, raw)
    serie = serie.strip().upper() if serie else None
    numero = numero.strip() if numero else None
    if serie and serie.isdigit():
        serie = f"F{serie}"
    if not numero:
        return None, None, None
    tipo = "BOLETA" if serie and serie.startswith("B") else "FACTURA"
    return tipo, serie, numero


def _column_letter(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _xlsx_cell(ref, value=None, formula=None, style=None, strings=None):
    style_attribute = f' s="{style}"' if style is not None else ""
    if formula is not None:
        return f'<c r="{ref}"{style_attribute}><f>{escape(formula)}</f><v></v></c>'
    if isinstance(value, (int, float, Decimal)):
        return f'<c r="{ref}"{style_attribute}><v>{value}</v></c>'
    return f'<c r="{ref}"{style_attribute} t="s"><v>{strings[str(value or "")]}</v></c>'


def _xlsx_sheet(rows, widths, strings, formulas=None):
    xml_rows = []
    for row_number, row in enumerate(rows, start=1):
        cells = []
        for column_number, value in enumerate(row, start=1):
            ref = f"{_column_letter(column_number)}{row_number}"
            formula = (formulas or {}).get((row_number, column_number))
            cells.append(_xlsx_cell(ref, value, formula, 4 if row_number == 1 else None, strings))
        xml_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    columns = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>{columns}</cols><sheetData>{"".join(xml_rows)}</sheetData>
  <autoFilter ref="A1:{_column_letter(len(rows[0]))}{max(1, len(rows))}"/>
  <pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>
</worksheet>'''


def _write_report(path, total_rows, outcomes, rejected):
    path.parent.mkdir(parents=True, exist_ok=True)
    codes = sorted(code for code in outcomes if code != "READY")
    summary_rows = [["Legacy IO expediente/comprobante sync", "Count"]]
    summary_rows.append(["CSV rows processed", total_rows])
    summary_rows.append(["Eligible rows", None])
    summary_rows.append(["Rejected or unmatched data rows", None])
    for code in codes:
        summary_rows.append([code, None])
    detail_headers = [
        "CSV_ROW", "REASON_CODE", "LEGACY_IO_ID", "EXPEDIENTE", "NROFACTURA",
        "FECOMPRO", "TOTAL", "MATCHED_LIQUIDACION_ID", "DETAIL",
    ]
    detail_rows = [detail_headers] + rejected
    summary_formulas = {
        (3, 2): "B2-B4",
        (4, 2): f"COUNTA('Rejections'!A2:A{len(detail_rows)})",
    }
    for row_number, code in enumerate(codes, start=5):
        summary_formulas[(row_number, 2)] = f'COUNTIF(\'Rejections\'!B2:B{len(detail_rows)},A{row_number})'
    strings = {}
    string_count = 0
    for row_number, row in enumerate(summary_rows, start=1):
        for column_number, value in enumerate(row, start=1):
            if (row_number, column_number) not in summary_formulas and not isinstance(value, (int, float, Decimal)):
                strings.setdefault(str(value or ""), len(strings))
                string_count += 1
    for row in detail_rows:
        for value in row:
            if not isinstance(value, (int, float, Decimal)):
                strings.setdefault(str(value or ""), len(strings))
                string_count += 1
    summary_xml = _xlsx_sheet(summary_rows, [42, 18], strings, summary_formulas)
    detail_xml = _xlsx_sheet(detail_rows, [10, 30, 14, 24, 22, 16, 14, 42, 60], strings)
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>'''
    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><calcPr calcMode="auto" fullCalcOnLoad="1"/><sheets><sheet name="Summary" sheetId="1" r:id="rId1"/><sheet name="Rejections" sheetId="2" r:id="rId2"/></sheets></workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs></styleSheet>'''
    shared_strings = "".join(f"<si><t>{escape(value)}</t></si>" for value in strings)
    shared_strings_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{string_count}" uniqueCount="{len(strings)}">{shared_strings}</sst>'''
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/sharedStrings.xml", shared_strings_xml)
        archive.writestr("xl/worksheets/sheet1.xml", summary_xml)
        archive.writestr("xl/worksheets/sheet2.xml", detail_xml)


class Command(BaseCommand):
    help = "Safely sync expediente and active comprobante for existing legacy IO records."

    def add_arguments(self, parser):
        parser.add_argument("--sync-expediente-comprobante", action="store_true")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--data-path")
        parser.add_argument("--report-path")
        parser.add_argument("--limit", type=int)

    def handle(self, *args, **options):
        if not options["sync_expediente_comprobante"]:
            raise CommandError("Pass --sync-expediente-comprobante to run this narrow curation.")
        if options["apply"] and options["dry_run"]:
            raise CommandError("Use either --apply or --dry-run, not both.")
        if options["limit"] is not None and options["limit"] < 1:
            raise CommandError("--limit must be at least 1.")

        data_path = Path(options["data_path"]) if options["data_path"] else DEFAULT_DATA_PATH
        if not data_path.exists():
            raise CommandError(f"CSV not found: {data_path}")
        with data_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, delimiter=";")
            required = {"ID", "NROEXPDTE", "NROFACTURA", "FECOMPRO", "TOTAL"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise CommandError(f"CSV is missing required columns: {sorted(required)}")
            rows = list(reader)
        if options["limit"]:
            rows = rows[: options["limit"]]

        ids = {int(row["ID"]) for row in rows if str(row.get("ID", "")).strip().isdigit()}
        matched = {}
        for io in (
            LiquidacionInspeccionObra.objects.filter(numero__in=ids, liquidacion__legacy=True)
            .select_related("liquidacion")
            .prefetch_related("liquidacion__comprobantes")
        ):
            matched.setdefault(io.numero, []).append(io)

        outcomes = Counter()
        rejected = []
        ready = []
        for csv_row, row in enumerate(rows, start=2):
            legacy_id = row.get("ID", "").strip()
            expediente = row.get("NROEXPDTE", "").strip()
            detail = ""
            reason = None
            candidates = matched.get(int(legacy_id), []) if legacy_id.isdigit() else []
            if not legacy_id.isdigit():
                reason, detail = "INVALID_LEGACY_IO_ID", "ID is missing or not an integer."
            elif not candidates:
                reason, detail = "LEGACY_IO_NOT_FOUND", "No imported legacy IO exists with this ID."
            elif len(candidates) > 1:
                reason, detail = "AMBIGUOUS_LEGACY_IO_ID", f"{len(candidates)} imported legacy IO records share this ID."
            else:
                try:
                    tipo, serie, numero = _parse_invoice(row.get("NROFACTURA"))
                    monto = _parse_decimal(row.get("TOTAL"))
                except ValueError as exc:
                    reason = "INVALID_TOTAL"
                    detail = str(exc)
                try:
                    fecha = _parse_date(row.get("FECOMPRO"))
                except ValueError:
                    fecha = None
            liquidacion_id = ""
            if reason is None:
                io = candidates[0]
                liquidacion_id = str(io.liquidacion_id)
                active = [comp for comp in io.liquidacion.comprobantes.all() if comp.activo]
                comprobante = active[0] if len(active) == 1 and numero is not None else None
                if expediente or comprobante is not None:
                    ready.append((io.liquidacion, comprobante, expediente, tipo, serie, numero, fecha, monto))
                    outcomes["READY"] += 1
                elif numero is not None:
                    reason = "ACTIVE_COMPROBANTE_NOT_FOUND" if not active else "AMBIGUOUS_ACTIVE_COMPROBANTE"
                    detail = "The matched liquidation has no unique active comprobante to update."
                else:
                    reason, detail = "NO_UPDATABLE_FIELDS", "NROEXPDTE and NROFACTURA are blank."
            if reason:
                outcomes[reason] += 1
                rejected.append([
                    csv_row, reason, legacy_id, expediente, row.get("NROFACTURA", ""),
                    row.get("FECOMPRO", ""), row.get("TOTAL", ""), liquidacion_id, detail,
                ])

        if options["apply"]:
            with transaction.atomic():
                for liquidacion, comprobante, expediente, tipo, serie, numero, fecha, monto in ready:
                    if expediente:
                        liquidacion.expediente = expediente
                        liquidacion.save(update_fields=["expediente"])
                    if comprobante is not None:
                        comprobante.tipo_comprobante = tipo
                        comprobante.serie = serie
                        comprobante.numero = numero
                        comprobante.fecha_emision = fecha
                        if monto is not None:
                            comprobante.monto = monto
                        comprobante.save(
                            update_fields=[
                                "tipo_comprobante",
                                "serie",
                                "numero",
                                "fecha_emision",
                                "monto",
                            ]
                        )

        default_report = Path(__file__).resolve().parents[5] / "result" / "IO" / "sync_expediente_comprobante_report.xlsx"
        report_path = Path(options["report_path"]) if options["report_path"] else default_report
        _write_report(report_path, len(rows), outcomes, rejected)
        mode = "APPLY" if options["apply"] else "DRY-RUN"
        self.stdout.write(f"Mode: {mode}")
        self.stdout.write(f"CSV rows processed: {len(rows)}")
        self.stdout.write(f"Ready to update: {outcomes['READY']}")
        self.stdout.write(f"Rejection data rows written: {len(rejected)}")
        for code in sorted(code for code in outcomes if code != "READY"):
            self.stdout.write(f"{code}: {outcomes[code]}")
        self.stdout.write(f"Report: {report_path}")
