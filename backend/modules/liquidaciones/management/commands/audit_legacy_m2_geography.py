"""Audit imported legacy M2 liquidations against their canonical CSV sources.

This command is intentionally read-only with respect to the database. It only
reads imported HU/MS liquidations and municipality catalog rows, then writes an
auditable CSV report to ``result/``.
"""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.management.commands.import_legacy_habilitacion_urbana import (
    COL_CODPAGO,
    COL_ID,
    DEFAULT_DATA_PATH as HU_DEFAULT_DATA_PATH,
)
from modules.liquidaciones.management.commands.import_legacy_mecanica_suelos import (
    DEFAULT_DATA_PATH as MS_DEFAULT_DATA_PATH,
    _clean as clean_ms_value,
    _int as int_ms_value,
    _row_to_dict as ms_row_to_dict,
)


PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "result"
REPORT_FIELDS = [
    "tipo",
    "numero",
    "codpago_fuente",
    "municipio_esperado_codigo",
    "municipio_asignado",
    "estado",
    "recomendacion_cura",
]


class Command(BaseCommand):
    help = "Audita geografia de liquidaciones legacy M2 sin escribir en la base de datos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=("hu", "ms", "all"),
            default="all",
            help="Tipo a auditar: hu, ms o all (default).",
        )
        parser.add_argument(
            "--hu-csv",
            type=Path,
            default=HU_DEFAULT_DATA_PATH,
            help=f"CSV canonico HU (default: {HU_DEFAULT_DATA_PATH}).",
        )
        parser.add_argument(
            "--ms-csv",
            type=Path,
            default=MS_DEFAULT_DATA_PATH,
            help=f"CSV canonico MS (default: {MS_DEFAULT_DATA_PATH}).",
        )
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=DEFAULT_OUTPUT_DIR,
            help=f"Directorio de reportes (default: {DEFAULT_OUTPUT_DIR}).",
        )

    def handle(self, *args, **options):
        requested_type = options["type"]
        selected_types = ("hu", "ms") if requested_type == "all" else (requested_type,)
        source_paths = {"hu": options["hu_csv"], "ms": options["ms_csv"]}
        rows = []
        skipped = []

        for audit_type in selected_types:
            source_path = source_paths[audit_type]
            if not source_path.is_file():
                skipped.append((audit_type.upper(), source_path))
                continue
            rows.extend(self._audit_type(audit_type, source_path))

        output_dir = options["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"auditoria_legacy_m2_geografia_{timestamp}.csv"
        summary_path = output_dir / f"auditoria_legacy_m2_geografia_{timestamp}_resumen.csv"
        self._write_report(report_path, rows)

        summary = Counter(row["estado"] for row in rows)
        self._write_summary(summary_path, rows, source_paths, skipped)
        self.stdout.write(self.style.SUCCESS(f"Reporte: {report_path}"))
        self.stdout.write(f"Resumen: {summary_path}")
        self.stdout.write(f"Filas auditadas: {len(rows)}")
        self.stdout.write(
            "Resumen: " + ", ".join(
                f"{status}={count}" for status, count in sorted(summary.items())
            ) if summary else "Resumen: sin filas auditadas"
        )
        for audit_type, source_path in skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"{audit_type}: fuente no disponible; se omitio sin afectar otros tipos: {source_path}"
                )
            )

    def _audit_type(self, audit_type: str, source_path: Path) -> list[dict[str, str]]:
        source_by_numero = self._read_source(audit_type, source_path)
        model = (
            LiquidacionHabilitacionUrbana
            if audit_type == "hu"
            else LiquidacionMecanicaSuelos
        )
        imported = model.objects.select_related("liquidacion__municipalidad").all()
        municipality_by_code = {
            municipality.codigo.upper(): municipality
            for municipality in Municipalidad.objects.all()
            if municipality.codigo
        }

        return [
            self._build_report_row(
                audit_type,
                liquidation.numero,
                liquidation.liquidacion.municipalidad,
                source_by_numero.get(liquidation.numero),
                municipality_by_code,
            )
            for liquidation in imported
        ]

    def _read_source(self, audit_type: str, source_path: Path) -> dict[int, str]:
        if audit_type == "hu":
            return self._read_hu_source(source_path)
        return self._read_ms_source(source_path)

    def _read_hu_source(self, source_path: Path) -> dict[int, str]:
        source_by_numero = {}
        with source_path.open("r", encoding="utf-8-sig", newline="") as source_file:
            reader = csv.reader(source_file, delimiter=";")
            next(reader, None)
            for row in reader:
                if len(row) <= max(COL_ID, COL_CODPAGO):
                    continue
                try:
                    numero = int(float(row[COL_ID].strip()))
                except (TypeError, ValueError):
                    continue
                source_by_numero.setdefault(numero, row[COL_CODPAGO].strip().upper())
        return source_by_numero

    def _read_ms_source(self, source_path: Path) -> dict[int, str]:
        source_by_numero = {}
        with source_path.open("r", encoding="utf-8-sig", newline="") as source_file:
            reader = csv.DictReader(source_file, delimiter=";")
            for source_row in reader:
                row = ms_row_to_dict(source_row)
                numero = int_ms_value(row.get("NRO"))
                if numero is not None:
                    source_by_numero.setdefault(numero, (clean_ms_value(row.get("CODPAGO")) or "").upper())
        return source_by_numero

    def _build_report_row(
        self,
        audit_type: str,
        numero: int,
        assigned_municipality: Municipalidad | None,
        source_code: str | None,
        municipality_by_code: dict[str, Municipalidad],
    ) -> dict[str, str]:
        if source_code is None:
            status = "SIN_FILA_FUENTE"
            expected_municipality = None
        elif not source_code:
            status = "CODPAGO_VACIO"
            expected_municipality = None
        else:
            expected_municipality = municipality_by_code.get(source_code)
            if expected_municipality is None:
                status = "CODPAGO_DESCONOCIDO"
            elif assigned_municipality is None:
                status = "MUNICIPIO_FALTANTE"
            elif assigned_municipality.id != expected_municipality.id:
                status = "MUNICIPIO_NO_COINCIDE"
            else:
                status = "OK"

        return {
            "tipo": audit_type.upper(),
            "numero": str(numero),
            "codpago_fuente": source_code or "",
            "municipio_esperado_codigo": self._municipality_label(expected_municipality),
            "municipio_asignado": self._municipality_label(assigned_municipality),
            "estado": status,
            "recomendacion_cura": self._recommendation(status),
        }

    def _write_report(self, report_path: Path, rows: list[dict[str, str]]) -> None:
        with report_path.open("w", encoding="utf-8-sig", newline="") as report_file:
            writer = csv.DictWriter(report_file, fieldnames=REPORT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def _write_summary(
        self,
        summary_path: Path,
        rows: list[dict[str, str]],
        source_paths: dict[str, Path],
        skipped: list[tuple[str, Path]],
    ) -> None:
        counts = Counter((row["tipo"], row["estado"]) for row in rows)
        with summary_path.open("w", encoding="utf-8-sig", newline="") as summary_file:
            writer = csv.DictWriter(
                summary_file,
                fieldnames=("tipo", "estado", "cantidad", "fuente"),
            )
            writer.writeheader()
            for (audit_type, status), count in sorted(counts.items()):
                writer.writerow(
                    {
                        "tipo": audit_type,
                        "estado": status,
                        "cantidad": count,
                        "fuente": source_paths[audit_type.lower()],
                    }
                )
            for audit_type, source_path in skipped:
                writer.writerow(
                    {
                        "tipo": audit_type,
                        "estado": "FUENTE_NO_DISPONIBLE",
                        "cantidad": 0,
                        "fuente": source_path,
                    }
                )

    @staticmethod
    def _municipality_label(municipality: Municipalidad | None) -> str:
        if municipality is None:
            return ""
        return f"{municipality.codigo} | {municipality.nombre}"

    @staticmethod
    def _recommendation(status: str) -> str:
        recommendations = {
            "OK": "Sin accion.",
            "CODPAGO_VACIO": "Revisar el CODPAGO legacy y asignar municipio manualmente con evidencia.",
            "CODPAGO_DESCONOCIDO": "Dar de alta o corregir el codigo municipal antes de curar la liquidacion.",
            "MUNICIPIO_FALTANTE": "Asignar el municipio resuelto por CODPAGO tras revision manual.",
            "MUNICIPIO_NO_COINCIDE": "Validar la fuente y corregir manualmente la municipalidad asignada.",
            "SIN_FILA_FUENTE": "Localizar la fila legacy original antes de modificar la liquidacion.",
        }
        return recommendations[status]
