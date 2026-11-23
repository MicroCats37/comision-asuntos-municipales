"""Safely import monthly inspector RH data from the historical Excel workbooks."""

from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from modules.finanzas.domain.models.registro_pago_inspector import RegistroPagoInspector
from modules.finanzas.domain.schemas import RHInspectorCotizarIn, RHInspectorCotizarItemIn
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.flujos.rh_inspector_mensual_flujo import (
    RHInspectorMensualCrearFlujo,
    RHInspectorMensualCotizarFlujo,
)
from modules.liquidaciones.models import LiquidacionComprobante
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorOperacion,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.liquidaciones.domain.constants import TipoLiquidacion as TipoLiquidacionConstants
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevisionCapitulo,
)
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import (
    PerfilIngenieroCoreService,
)


DEFAULT_SOURCE = Path(__file__).resolve().parents[4] / "core_application" / "seeds" / "historico" / "rh_io"
MONTHS = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SETIEMBRE": 9, "SEPTIEMBRE": 9, "OCTUBRE": 10,
    "NOVIEMBRE": 11, "DICIEMBRE": 12,
}


def _text(value) -> str:
    return str(value or "").strip()


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _headers(ws):
    for row in ws.iter_rows():
        values = [_text(cell.value).upper() for cell in row]
        if "EXPEDIENTE" in values and any("INSP" in value and "MES" in value for value in values):
            return row[0].row, values
    return None, []


def _period(ws, values_ws) -> tuple[int, int] | None:
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "HLOOKUP(" in cell.value.upper():
                value = _text(values_ws[cell.coordinate].value).upper()
                for name, number in MONTHS.items():
                    match = re.search(rf"{name}\s+(20\d{{2}})", value)
                    if match:
                        return int(match.group(1)), number
    return None


def _ensure_inspector_io(cip: str, lcv, apply: bool):
    """Hydrate the collegiate profile and ensure its IO operation/link exists."""
    perfil, status = PerfilIngenieroCoreService().hydrate_perfil_from_cip(
        cip,
        dry_run=not apply,
        refresh_if_incomplete=True,
    )
    if perfil is None:
        return None, status
    inspector, _ = Inspector.objects.get_or_create(perfil_ingeniero=perfil)
    especialidades = list(
        EspecialidadRevisionCapitulo.objects.filter(capitulo_id=perfil.capitulo_id)
        .select_related("especialidad_revision")[:2]
    )
    if len(especialidades) != 1:
        return None, "SIN_ESPECIALIDAD_CAPITULO"
    categoria = lcv.categoria if lcv.categoria in {"1", "2", "3", "4"} else "1"
    tipo_io = TipoLiquidacion.objects.get(codigo=TipoLiquidacionConstants.INSPECCION_OBRA)
    operacion, _ = InspectorOperacion.objects.get_or_create(
        inspector=inspector,
        tipo_liquidacion=tipo_io,
        categoria=categoria,
        defaults={"especialidad_revision": especialidades[0].especialidad_revision},
    )
    if operacion.especialidad_revision_id != especialidades[0].especialidad_revision_id:
        operacion.especialidad_revision = especialidades[0].especialidad_revision
        operacion.save(update_fields=["especialidad_revision"])
    LiquidacionInspector.objects.get_or_create(
        liquidacion=lcv,
        inspector=inspector,
        defaults={
            "inspector_operacion": operacion,
            "especialidad_revision": operacion.especialidad_revision,
        },
    )
    return inspector, status


def _dry_run_inspector_status(cip: str, lcvs) -> str:
    """Validate whether the inspector setup exists or can be completed on apply."""
    perfil, status = PerfilIngenieroCoreService().hydrate_perfil_from_cip(
        cip,
        dry_run=True,
        refresh_if_incomplete=True,
    )
    if status == "ACTUALIZADO_DESDE_CIP" and perfil is not None and not perfil.capitulo_id:
        return "READY_AFTER_CIP_REFRESH"
    if perfil is None:
        return "READY_AFTER_CIP_HYDRATION" if status == "CREADO_DESDE_CIP" else status

    mappings = EspecialidadRevisionCapitulo.objects.filter(capitulo_id=perfil.capitulo_id)
    if mappings.count() != 1:
        return "SIN_ESPECIALIDAD_CAPITULO"
    inspector = Inspector.objects.filter(perfil_ingeniero=perfil).first()
    if inspector is None:
        return "READY_AFTER_INSPECTOR_SETUP"
    linked_ids = set(
        LiquidacionInspector.objects.filter(inspector=inspector, liquidacion__in=lcvs)
        .values_list("liquidacion_id", flat=True)
    )
    return "READY" if len(linked_ids) == len({lcv.id for lcv in lcvs}) else "READY_AFTER_INSPECTOR_SETUP"


class Command(BaseCommand):
    help = "Import historical monthly RH inspector workbooks; dry-run by default."

    def add_arguments(self, parser):
        parser.add_argument("--source", default=str(DEFAULT_SOURCE))
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--report-path", default=None)
        parser.add_argument("--limit", type=int)

    def handle(self, *args, **options):
        source = Path(options["source"])
        files = [source] if source.is_file() else sorted(source.glob("*.xlsx"))
        if not files:
            raise CommandError(f"No XLSX files found at {source}")
        if options["limit"]:
            files = files[:options["limit"]]
        report_path = Path(options["report_path"] or Path(__file__).resolve().parents[5] / "result" / "IO" / "legacy_rh_inspector_migration.csv")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        core = FinanzasCoreService()
        crear = RHInspectorMensualCrearFlujo(core, RHInspectorMensualCotizarFlujo(core))
        outcomes = []

        for path in files:
            formula_ws = load_workbook(path, data_only=False).active
            values_ws = load_workbook(path, data_only=True).active
            header_row, headers = _headers(values_ws)
            period = _period(formula_ws, values_ws)
            cip_match = re.search(r"CIP\s*(\d+)", " ".join(_text(cell.value) for row in values_ws.iter_rows() for cell in row), re.I)
            if not header_row or not period or not cip_match:
                outcomes.append([path.name, "", "", "", "", "SKIPPED_TEMPLATE", "Missing headers, period, or CIP"])
                continue
            header_index = {value: index + 1 for index, value in enumerate(headers)}
            exp_col = header_index["EXPEDIENTE"]
            comp_col = next((column for name, column in header_index.items() if "COMP" in name), None)
            month_col = next((column for name, column in header_index.items() if "INSP" in name and "MES" in name), None)
            prev_col = next((column for name, column in header_index.items() if "PAGADAS" in name), None)
            if not all((comp_col, month_col, prev_col)):
                outcomes.append([path.name, cip_match.group(1), *period, "", "SKIPPED_TEMPLATE", "Missing required columns"])
                continue
            items = []
            rows = []
            for row in range(header_row + 1, values_ws.max_row + 1):
                expediente = _text(values_ws.cell(row, exp_col).value)
                comprobante = _text(values_ws.cell(row, comp_col).value)
                if not expediente or not comprobante:
                    continue
                serie, numero = (comprobante.split("-", 1) + [""])[:2]
                match = LiquidacionComprobante.objects.filter(
                    activo=True,
                    liquidacion_general__expediente=expediente,
                    serie__iexact=serie,
                    numero__iexact=numero,
                ).select_related("liquidacion_general").first()
                if not match:
                    comprobante_matches = list(
                        LiquidacionComprobante.objects.filter(
                            activo=True,
                            serie__iexact=serie,
                            numero__iexact=numero,
                        ).select_related("liquidacion_general")[:2]
                    )
                    if len(comprobante_matches) == 1:
                        match = comprobante_matches[0]
                    elif len(comprobante_matches) > 1:
                        outcomes.append([
                            path.name, cip_match.group(1), period[0], period[1], row,
                            "AMBIGUOUS_COMPROBANTE", f"{expediente} | {comprobante}",
                        ])
                        continue
                visitas_mes = _int(values_ws.cell(row, month_col).value)
                previas = _int(values_ws.cell(row, prev_col).value)
                if not match:
                    outcomes.append([path.name, cip_match.group(1), period[0], period[1], row, "NO_MATCH_COMPROBANTE", f"{expediente} | {comprobante}"])
                    continue
                lcv = LiquidacionPorCategoriaVisitas.objects.filter(
                    liquidacion_general=match.liquidacion_general,
                ).first()
                if not lcv:
                    outcomes.append([path.name, cip_match.group(1), period[0], period[1], row, "NO_IO", expediente])
                    continue
                rows.append((row, lcv, previas, visitas_mes))
                if visitas_mes:
                    items.append(RHInspectorCotizarItemIn(liquidacion_categoria_visitas_id=str(lcv.id), cantidad_visitas=visitas_mes))
            if not items:
                outcomes.append([path.name, cip_match.group(1), period[0], period[1], "", "NO_MONTHLY_VISITS", "No valid rows"])
                continue
            payload = RHInspectorCotizarIn(cip=cip_match.group(1), periodo=period[0], mes=period[1], items=items)
            try:
                if options["apply"]:
                    with transaction.atomic():
                        for _, lcv, _, _ in rows:
                            inspector, inspector_status = _ensure_inspector_io(
                                cip_match.group(1), lcv, apply=True,
                            )
                            if inspector is None:
                                raise CommandError(f"Inspector {cip_match.group(1)}: {inspector_status}")
                        for _, lcv, previas, _ in rows:
                            if previas:
                                RegistroPagoInspector.objects.get_or_create(liquidacion_por_categoria_visitas=lcv, periodo=period[0], mes=1, recibo_mensual=None, defaults={"inspecciones_pagadas": previas, "fecha_registro": date(period[0], 1, 1)})
                        crear.crear(payload)
                else:
                    setup_status = _dry_run_inspector_status(
                        cip_match.group(1), [lcv for _, lcv, _, _ in rows],
                    )
                    if setup_status != "READY":
                        if setup_status.startswith("READY_AFTER_"):
                            outcomes.append([path.name, cip_match.group(1), period[0], period[1], "", setup_status, f"{len(items)} monthly rows"])
                            continue
                        raise CommandError(f"Inspector {cip_match.group(1)}: {setup_status}")
                    RHInspectorMensualCotizarFlujo(core).cotizar(payload)
                outcomes.append([path.name, cip_match.group(1), period[0], period[1], "", "READY" if not options["apply"] else "IMPORTED", f"{len(items)} monthly rows"])
            except Exception as exc:
                outcomes.append([path.name, cip_match.group(1), period[0], period[1], "", "REJECTED", str(exc)])

        with report_path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["WORKBOOK", "CIP", "YEAR", "MONTH", "SOURCE_ROW", "STATUS", "DETAIL"])
            writer.writerows(outcomes)
        counts = Counter(row[5] for row in outcomes)
        self.stdout.write(f"Mode: {'APPLY' if options['apply'] else 'DRY-RUN'}")
        self.stdout.write(f"Report: {report_path}")
        self.stdout.write(f"Outcomes: {dict(counts)}")
