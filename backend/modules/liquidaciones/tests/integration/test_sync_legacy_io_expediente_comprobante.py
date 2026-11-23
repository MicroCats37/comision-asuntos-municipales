import csv
import zipfile
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import LiquidacionInspeccionObra
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import LiquidacionComprobante
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral


@pytest.fixture
def legacy_io_with_comprobante(municipalidad, proyecto, tipo_inspeccion_obra):
    liquidacion = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_inspeccion_obra,
        expediente="OLD-EXP",
        sub_total=Decimal("100.00"),
        total=Decimal("118.00"),
        legacy=True,
    )
    LiquidacionInspeccionObra.objects.create(liquidacion=liquidacion, numero=501)
    comprobante = LiquidacionComprobante.objects.create(
        liquidacion_general=liquidacion,
        activo=True,
        tipo_comprobante="FACTURA",
        serie="F001",
        numero="OLD",
        fecha_emision=date(2020, 1, 1),
        monto=Decimal("118.00"),
    )
    return liquidacion, comprobante


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["ID", "NROEXPDTE", "NROFACTURA", "FECOMPRO", "TOTAL"], delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.django_db
def test_dry_run_preserves_records_and_writes_rejection_report(tmp_path, legacy_io_with_comprobante):
    liquidacion, comprobante = legacy_io_with_comprobante
    data_path = tmp_path / "io.csv"
    report_path = tmp_path / "report.xlsx"
    write_csv(data_path, [
        {"ID": "501", "NROEXPDTE": "NEW-EXP", "NROFACTURA": "003-00112077", "FECOMPRO": "20/08/2026", "TOTAL": "250.00"},
        {"ID": "999", "NROEXPDTE": "NO-IO", "NROFACTURA": "001-1", "FECOMPRO": "20/08/2026", "TOTAL": "1"},
    ])

    call_command("sync_legacy_io_expediente_comprobante", "--sync-expediente-comprobante", "--data-path", data_path, "--report-path", report_path)

    liquidacion.refresh_from_db()
    comprobante.refresh_from_db()
    assert liquidacion.expediente == "OLD-EXP"
    assert comprobante.numero == "OLD"
    assert report_path.exists()
    with zipfile.ZipFile(report_path) as report:
        workbook = report.read("xl/workbook.xml").decode()
        strings = report.read("xl/sharedStrings.xml").decode()
        rejections_xml = report.read("xl/worksheets/sheet2.xml").decode()
    assert 'name="Summary"' in workbook
    assert 'name="Rejections"' in workbook
    assert "LEGACY_IO_NOT_FOUND" in strings
    assert rejections_xml.count("<row ") == 2  # Header plus one rejected data row.


@pytest.mark.django_db
def test_apply_updates_only_expediente_and_active_comprobante(tmp_path, legacy_io_with_comprobante):
    liquidacion, comprobante = legacy_io_with_comprobante
    data_path = tmp_path / "io.csv"
    write_csv(data_path, [{"ID": "501", "NROEXPDTE": "NEW-EXP", "NROFACTURA": "003-00112077", "FECOMPRO": "20/08/2026", "TOTAL": "250.00"}])

    call_command("sync_legacy_io_expediente_comprobante", "--sync-expediente-comprobante", "--apply", "--data-path", data_path, "--report-path", tmp_path / "report.xlsx")

    liquidacion.refresh_from_db()
    comprobante.refresh_from_db()
    assert liquidacion.expediente == "NEW-EXP"
    assert comprobante.tipo_comprobante == "FACTURA"
    assert comprobante.serie == "F003"
    assert comprobante.numero == "00112077"
    assert comprobante.fecha_emision == date(2026, 8, 20)
    assert comprobante.monto == Decimal("250.00")
    assert LiquidacionInspeccionObra.objects.count() == 1
    assert LiquidacionComprobante.objects.filter(liquidacion_general=liquidacion).count() == 1


@pytest.mark.django_db
def test_apply_keeps_optional_expediente_and_nulls_invalid_receipt_date(tmp_path, legacy_io_with_comprobante):
    liquidacion, comprobante = legacy_io_with_comprobante
    data_path = tmp_path / "io.csv"
    write_csv(data_path, [{"ID": "501", "NROEXPDTE": "", "NROFACTURA": "003-00112077", "FECOMPRO": "not-a-date", "TOTAL": "250.00"}])

    call_command("sync_legacy_io_expediente_comprobante", "--sync-expediente-comprobante", "--apply", "--data-path", data_path, "--report-path", tmp_path / "report.xlsx")

    liquidacion.refresh_from_db()
    comprobante.refresh_from_db()
    assert liquidacion.expediente == "OLD-EXP"
    assert comprobante.numero == "00112077"
    assert comprobante.fecha_emision is None
