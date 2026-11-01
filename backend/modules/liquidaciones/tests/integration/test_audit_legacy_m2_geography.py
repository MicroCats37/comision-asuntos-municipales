"""Integration coverage for the read-only legacy M2 geography audit."""

import csv

import pytest
from django.core.management import call_command

from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.liquidaciones.domain.models.proyecto import Proyecto


@pytest.mark.django_db
def test_audit_reports_hu_mismatch_without_database_writes(
    municipalidad,
    proyecto,
    tmp_path,
):
    """A mismatched CODPAGO is reported and all audited models remain unchanged."""
    expected_municipality = Municipalidad.objects.create(
        codigo="M002",
        nombre="Municipalidad Esperada",
        distrito=municipalidad.distrito,
    )
    tipo_hu = TipoLiquidacion.objects.create(
        codigo="HABILITACION_URBANA",
        nombre="Habilitacion Urbana",
    )
    general = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_hu,
        sub_total="100.00",
        total="118.00",
        legacy=True,
    )
    LiquidacionHabilitacionUrbana.objects.create(liquidacion=general, numero=1200)
    counts_before = {
        "municipalities": Municipalidad.objects.count(),
        "projects": Proyecto.objects.count(),
        "generals": LiquidacionGeneral.objects.count(),
        "hu": LiquidacionHabilitacionUrbana.objects.count(),
    }

    source_path = tmp_path / "HU_ALL.csv"
    source_path.write_text(
        ";".join(f"COL_{index}" for index in range(18))
        + "\n"
        + ";".join(["1200"] + [""] * 16 + [expected_municipality.codigo])
        + "\n",
        encoding="utf-8",
    )

    call_command(
        "audit_legacy_m2_geography",
        "--type",
        "hu",
        "--hu-csv",
        str(source_path),
        "--output-dir",
        str(tmp_path),
    )

    report_path = next(
        path
        for path in tmp_path.glob("auditoria_legacy_m2_geografia_*.csv")
        if not path.name.endswith("_resumen.csv")
    )
    with report_path.open(encoding="utf-8-sig", newline="") as report_file:
        report_rows = list(csv.DictReader(report_file))

    assert report_rows == [
        {
            "tipo": "HU",
            "numero": "1200",
            "codpago_fuente": "M002",
            "municipio_esperado_codigo": "M002 | Municipalidad Esperada",
            "municipio_asignado": "M001 | Municipalidad de Miraflores",
            "estado": "MUNICIPIO_NO_COINCIDE",
            "recomendacion_cura": "Validar la fuente y corregir manualmente la municipalidad asignada.",
        }
    ]
    assert {
        "municipalities": Municipalidad.objects.count(),
        "projects": Proyecto.objects.count(),
        "generals": LiquidacionGeneral.objects.count(),
        "hu": LiquidacionHabilitacionUrbana.objects.count(),
    } == counts_before
