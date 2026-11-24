"""Safely import monthly inspector RH data from the historical Excel workbooks."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from modules.finanzas.domain.models.registro_pago_inspector import RegistroPagoInspector
from modules.finanzas.domain.models.recibo_honorario_inspector_mensual import (
    ReciboHonorarioInspectorMensual,
)
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
    EspecialidadRevision,
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


def _match_text(value) -> str:
    return " ".join(
        "".join(
            char for char in unicodedata.normalize("NFKD", _text(value).upper())
            if not unicodedata.combining(char)
        ).split()
    )


def _composite_key(owner: str, district: str, assigned_visits: int) -> tuple[str, str, int]:
    return _match_text(owner), _match_text(district), assigned_visits


def _composite_matches(composite_index: dict, owner: str, district: str, assigned_visits: int, used_lcv_ids: set):
    """Find unused IO rows by the historical owner, district and assigned visits key."""
    if not owner or not district or not assigned_visits:
        return []
    return [
        lcv for lcv in composite_index.get(_composite_key(owner, district, assigned_visits), [])
        if lcv.id not in used_lcv_ids
    ][:2]


def _headers(ws):
    for row in ws.iter_rows():
        values = [_text(cell.value).upper() for cell in row]
        if any(value.startswith("EXPEDIENTE") for value in values) and any(
            "INSP" in value and "MES" in value for value in values
        ):
            return row[0].row, values
    return None, []


def _period(ws, values_ws) -> tuple[int, int] | None:
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "HLOOKUP(" in cell.value.upper():
                value = _text(values_ws[cell.coordinate].value).upper()
                for name, number in MONTHS.items():
                    match = re.search(rf"{name}\s*(20\d{{2}})", value)
                    if match:
                        return int(match.group(1)), number
    return None


def _especialidad_por_capitulo(capitulo_id):
    """Specialty of review resolved from the inspector's professional chapter.

    Falls back to the generic inspection specialty when the chapter has no
    mapping, so the migration is not blocked; the case is reported instead.
    """
    if not capitulo_id:
        return None, "SIN_CAPITULO"
    mapeos = list(
        EspecialidadRevisionCapitulo.objects.filter(capitulo_id=capitulo_id)
        .select_related("especialidad_revision")[:2]
    )
    if len(mapeos) == 1:
        return mapeos[0].especialidad_revision, None
    if len(mapeos) > 1:
        return None, "CAPITULO_AMBIGUO"
    generica = EspecialidadRevision.objects.filter(
        nombre__iexact="Inspección de Obra"
    ).first()
    if generica is None:
        generica = EspecialidadRevision.objects.order_by("nombre").first()
    if generica is None:
        return None, "SIN_ESPECIALIDAD_REVISION"
    return generica, "CAPITULO_SIN_MAPEO"


def _ensure_inspector_io(cip: str, lcv, apply: bool, cache: dict | None = None):
    """Hydrate the collegiate profile and link the IO to the inspector.

    The link is created WITHOUT operativity (``inspector_operacion`` stays
    null, legacy style). The review specialty comes from the inspector's
    chapter. No operativity is created nor modified.

    ``cache`` memoizes the CIP resolution for the whole run: the CIP endpoint
    is consulted once per inspector, not once per row.
    """
    inspector = None
    especialidad = None
    status = ""
    if cache is not None and cip in cache:
        inspector, especialidad, status = cache[cip]
        if inspector is None or especialidad is None:
            return None, status
    else:
        perfil, status = PerfilIngenieroCoreService().hydrate_perfil_from_cip(
            cip,
            dry_run=not apply,
            refresh_if_incomplete=True,
        )
        if perfil is None:
            if cache is not None:
                cache[cip] = (None, None, status)
            return None, status
        inspector, _ = Inspector.objects.get_or_create(perfil_ingeniero=perfil)
        especialidad, especialidad_status = _especialidad_por_capitulo(perfil.capitulo_id)
        if especialidad is None:
            if cache is not None:
                cache[cip] = (None, None, especialidad_status)
            return None, especialidad_status
        status = especialidad_status or status
        if cache is not None:
            cache[cip] = (inspector, especialidad, status)
    LiquidacionInspector.objects.get_or_create(
        liquidacion=lcv,
        inspector=inspector,
        defaults={
            "inspector_operacion": None,
            "especialidad_revision": especialidad,
        },
    )
    return inspector, status


def _rh_ya_importado(cip: str, periodo: int, mes: int) -> bool:
    """True when a monthly receipt already exists for that inspector and period."""
    inspector = Inspector.objects.filter(perfil_ingeniero__cip=cip).first()
    if inspector is None:
        return False
    return ReciboHonorarioInspectorMensual.objects.filter(
        inspector=inspector, periodo=periodo, mes=mes
    ).exists()


def _diagnostico_sin_match(expediente: str, owner: str, district: str, visitas: int, index: dict) -> str:
    """High-level reason why an Excel row could not be linked to an IO row.

    The reason is expressed in business terms so it can be reviewed without
    reading the code: the row is not silently dropped, it is explained.
    """
    if expediente.upper() == "DATO":
        return "Fila de relleno del Excel: no contiene datos de una liquidacion real."
    expedientes = index["expedientes"]
    por_propietario = index["por_propietario"]
    por_propietario_distrito = index["por_propietario_distrito"]
    clave_expediente = _match_text(expediente)
    clave_propietario = _match_text(owner)
    clave_distrito = _match_text(district)
    if clave_expediente in expedientes:
        return (
            "El expediente SI existe en la base, pero con otros datos: el propietario, "
            "el distrito o las inspecciones programadas del Excel no coinciden con los registrados."
        )
    if (clave_propietario, clave_distrito) in por_propietario_distrito:
        return (
            "El propietario y el distrito existen en la base, pero con otro numero "
            "de inspecciones programadas (clave con visitas no coincide)."
        )
    if clave_propietario in por_propietario:
        return (
            "El propietario existe en la base, pero en otro distrito: la clave "
            "propietario + distrito no coincide con ninguna liquidacion IO."
        )
    return (
        "No existe en la base: ni el expediente ni el propietario + distrito "
        "aparecen en ninguna liquidacion IO."
    )


def _dry_run_inspector(cip: str):
    """Resolve the inspector of a CIP without writing to the database."""
    perfil, _ = PerfilIngenieroCoreService().hydrate_perfil_from_cip(
        cip,
        dry_run=True,
        refresh_if_incomplete=True,
    )
    if perfil is None:
        return None
    return Inspector.objects.filter(perfil_ingeniero=perfil).first()


def _resolve_operativity_key(inspector, lcv) -> str:
    """Operativity that ends up attached to the IO link for this inspector.

    Links created by this command keep a null operativity (legacy style), so
    they are grouped together with the null group. A monthly receipt cannot mix
    two different operativities, so items are grouped by this key.
    """
    if inspector is None:
        return "SIN_INSPECTOR"
    link = (
        LiquidacionInspector.objects.filter(liquidacion=lcv, inspector=inspector)
        .select_related("inspector_operacion")
        .first()
    )
    if link is not None and link.inspector_operacion_id:
        return str(link.inspector_operacion_id)
    return "SIN_OPERATIVIDAD"


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

    especialidad, especialidad_status = _especialidad_por_capitulo(perfil.capitulo_id)
    if especialidad is None:
        return especialidad_status
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
        mapping_rows = []
        pending_rows = []
        inspector_cache = {}
        match_counts = Counter()
        monthly_rows_ready = 0
        monthly_receipts = 0
        composite_index = {}
        diagnostico_index = {"expedientes": set(), "por_propietario": {}, "por_propietario_distrito": {}}
        for lcv in LiquidacionPorCategoriaVisitas.objects.select_related(
            "liquidacion_general__proyecto__distrito",
        ):
            project = lcv.liquidacion_general.proyecto
            owner = project.nombre_propietario
            district = project.distrito.nombre if project.distrito else ""
            key = _composite_key(owner, district, lcv.cantidad_visitas)
            composite_index.setdefault(key, []).append(lcv)
            expediente = lcv.liquidacion_general.expediente
            if expediente:
                diagnostico_index["expedientes"].add(_match_text(expediente))
            clave_propietario = _match_text(owner)
            clave_distrito = _match_text(district)
            diagnostico_index["por_propietario"].setdefault(clave_propietario, []).append((clave_distrito, lcv.cantidad_visitas))
            diagnostico_index["por_propietario_distrito"].setdefault((clave_propietario, clave_distrito), []).append(lcv.cantidad_visitas)

        for path in files:
            formula_ws = load_workbook(path, data_only=False).active
            values_ws = load_workbook(path, data_only=True).active
            header_row, headers = _headers(values_ws)
            period = _period(formula_ws, values_ws)
            cip_match = re.search(r"CIP\s*(\d+)", " ".join(_text(cell.value) for row in values_ws.iter_rows() for cell in row), re.I)
            if not header_row or not period or not cip_match:
                outcomes.append([path.name, "", "", "", "", "SKIPPED_TEMPLATE", "Missing headers, period, or CIP"])
                continue
            # El CIP del Excel puede venir con menos de 6 digitos; la base lo
            # guarda con cero a la izquierda y el flujo lo busca exacto.
            cip = str(cip_match.group(1)).zfill(6)[:6]
            header_index = {value: index + 1 for index, value in enumerate(headers)}
            exp_col = next((column for name, column in header_index.items() if name.startswith("EXPEDIENTE")), None)
            comp_col = next((column for name, column in header_index.items() if "COMP" in name), None)
            month_col = next((column for name, column in header_index.items() if "INSP" in name and "MES" in name), None)
            prev_col = next((column for name, column in header_index.items() if "PAGADAS" in name), None)
            owner_col = next((column for name, column in header_index.items() if "ADMINISTR" in name), None)
            district_col = header_index.get("DISTRITO")
            assigned_visits_col = next((column for name, column in header_index.items() if "PROGRAM" in name), None)
            if not all((exp_col, comp_col, month_col, prev_col, owner_col, district_col, assigned_visits_col)):
                outcomes.append([path.name, cip, *period, "", "SKIPPED_TEMPLATE", "Missing required columns"])
                continue
            items = []
            rows = []
            used_lcv_ids = set()

            def registrar_equivalencia(source_row, expediente, comprobante, owner, district, programadas, visitas_mes, previas, match_type, lcv, estado, motivo=""):
                registro = [
                    path.name, cip, period[0], period[1], source_row,
                    expediente, comprobante, owner, district, programadas, visitas_mes, previas,
                    match_type or "", estado, motivo,
                    str(lcv.id) if lcv is not None else "",
                    lcv.liquidacion_general.expediente if lcv is not None else "",
                    lcv.categoria if lcv is not None else "",
                    lcv.cantidad_visitas if lcv is not None else "",
                ]
                mapping_rows.append(registro)
                if estado != "ASIGNADO":
                    pending_rows.append(registro)

            for row in range(header_row + 1, values_ws.max_row + 1):
                expediente = _text(values_ws.cell(row, exp_col).value)
                comprobante = _text(values_ws.cell(row, comp_col).value)
                if not expediente or not comprobante:
                    continue
                if expediente.upper() in {"TOTAL", "TOTALES", "SUB TOTAL", "SUBTOTAL"}:
                    continue
                owner = _text(values_ws.cell(row, owner_col).value)
                district = _text(values_ws.cell(row, district_col).value)
                visitas_mes = _int(values_ws.cell(row, month_col).value)
                previas = _int(values_ws.cell(row, prev_col).value)
                assigned_visits = _int(values_ws.cell(row, assigned_visits_col).value)
                serie, numero = (comprobante.split("-", 1) + [""])[:2]
                match = LiquidacionComprobante.objects.filter(
                    activo=True,
                    liquidacion_general__expediente=expediente,
                    serie__iexact=serie,
                    numero__iexact=numero,
                ).select_related("liquidacion_general").first()
                match_type = "EXPEDIENTE_COMPROBANTE" if match else None
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
                        match_type = "COMPROBANTE"
                    elif len(comprobante_matches) > 1:
                        outcomes.append([
                            path.name, cip, period[0], period[1], row,
                            "AMBIGUOUS_COMPROBANTE", f"{expediente} | {comprobante}",
                        ])
                        registrar_equivalencia(
                            row, expediente, comprobante, owner, district, assigned_visits,
                            visitas_mes, previas, match_type, None, "AMBIGUOUS_COMPROBANTE",
                            "El numero de comprobante apunta a mas de una liquidacion IO: "
                            "no se puede decidir a cual pertenece la fila.",
                        )
                        continue
                if not match:
                    composite = _composite_matches(
                        composite_index,
                        owner,
                        district,
                        assigned_visits,
                        used_lcv_ids,
                    )
                    if len(composite) == 1:
                        lcv = composite[0]
                        match_type = "COMPOSITE"
                        outcomes.append([
                            path.name, cip, period[0], period[1], row,
                            "MATCH_COMPOSITE", f"{owner} | {district} | {assigned_visits}",
                        ])
                    elif len(composite) > 1:
                        outcomes.append([path.name, cip, period[0], period[1], row, "AMBIGUOUS_COMPOSITE", f"{owner} | {district} | {assigned_visits}"])
                        registrar_equivalencia(
                            row, expediente, comprobante, owner, district, assigned_visits,
                            visitas_mes, previas, match_type, None, "AMBIGUOUS_COMPOSITE",
                            "La clave propietario + distrito + inspecciones programadas devuelve "
                            "mas de una liquidacion IO posible: no se puede decidir cual es.",
                        )
                        continue
                    else:
                        outcomes.append([path.name, cip, period[0], period[1], row, "NO_MATCH_COMPOSITE", f"{expediente} | {comprobante}"])
                        registrar_equivalencia(
                            row, expediente, comprobante, owner, district, assigned_visits,
                            visitas_mes, previas, match_type, None, "NO_MATCH_COMPOSITE",
                            _diagnostico_sin_match(
                                expediente, owner, district, assigned_visits, diagnostico_index
                            ),
                        )
                        continue
                else:
                    lcv = LiquidacionPorCategoriaVisitas.objects.filter(
                        liquidacion_general=match.liquidacion_general,
                    ).select_related("liquidacion_general").first()
                if not lcv:
                    outcomes.append([path.name, cip, period[0], period[1], row, "NO_IO", expediente])
                    registrar_equivalencia(
                        row, expediente, comprobante, owner, district, assigned_visits,
                        visitas_mes, previas, match_type, None, "NO_IO",
                        "La liquidacion existe en la base pero no tiene el detalle de "
                        "visitas IO que necesita el calculo de honorarios.",
                    )
                    continue
                if lcv.id in used_lcv_ids:
                    outcomes.append([path.name, cip, period[0], period[1], row, "DUPLICATE_IO", expediente])
                    registrar_equivalencia(
                        row, expediente, comprobante, owner, district, assigned_visits,
                        visitas_mes, previas, match_type, lcv, "DUPLICATE_IO",
                        "La liquidacion IO ya fue asignada a otra fila del mismo libro: "
                        "el Excel reparte las visitas del mes de una misma liquidacion "
                        "en varias filas y la regla de una IO por fila las bloquea.",
                    )
                    continue
                used_lcv_ids.add(lcv.id)
                if visitas_mes:
                    saldo = (lcv.cantidad_visitas or 0) - previas
                    if visitas_mes > saldo:
                        outcomes.append([
                            path.name, cip, period[0], period[1], row,
                            "REJECTED_SALDO",
                            f"{expediente} | visitas={visitas_mes} previas={previas} programadas={lcv.cantidad_visitas} saldo={saldo}",
                        ])
                        registrar_equivalencia(
                            row, expediente, comprobante, owner, district, assigned_visits,
                            visitas_mes, previas, match_type, lcv, "REJECTED_SALDO",
                            f"Las visitas del mes ({visitas_mes}) superan el saldo disponible "
                            f"(programadas {lcv.cantidad_visitas} - ya pagadas {previas} = {saldo}). "
                            "Es una inconsistencia del Excel.",
                        )
                        continue
                match_counts[match_type] += 1
                rows.append((row, lcv, previas, visitas_mes))
                registrar_equivalencia(row, expediente, comprobante, owner, district, assigned_visits, visitas_mes, previas, match_type, lcv, "ASIGNADO")
                if visitas_mes:
                    monthly_rows_ready += 1
                    items.append({
                        "liquidacion_categoria_visitas_id": str(lcv.id),
                        "cantidad_visitas": visitas_mes,
                    })
            if not items:
                outcomes.append([path.name, cip, period[0], period[1], "", "NO_MONTHLY_VISITS", "No valid rows"])
                continue
            payload = RHInspectorCotizarIn(cip=cip, periodo=period[0], mes=period[1], items=items)
            if _rh_ya_importado(cip, period[0], period[1]):
                outcomes.append([
                    path.name, cip, period[0], period[1], "",
                    "YA_IMPORTADO", f"{len(items)} monthly rows (recibo existente)",
                ])
                continue
            try:
                if options["apply"]:
                    with transaction.atomic():
                        inspector = None
                        for _, lcv, _, _ in rows:
                            inspector, inspector_status = _ensure_inspector_io(
                                cip, lcv, apply=True, cache=inspector_cache,
                            )
                            if inspector is None:
                                raise CommandError(f"Inspector {cip}: {inspector_status}")
                        for _, lcv, previas, _ in rows:
                            if previas:
                                RegistroPagoInspector.objects.get_or_create(liquidacion_por_categoria_visitas=lcv, periodo=period[0], mes=1, recibo_mensual=None, defaults={"inspecciones_pagadas": previas, "fecha_registro": date(period[0], 1, 1)})
                        groups = defaultdict(list)
                        for _, lcv, _, visitas_mes in rows:
                            if not visitas_mes:
                                continue
                            groups[_resolve_operativity_key(inspector, lcv)].append((lcv, visitas_mes))
                        # El flujo tolera items sin operatividad junto a UNA sola
                        # operatividad, asi que el grupo nulo se fusiona con el
                        # primero para no partir el RH sin necesidad.
                        if len(groups) > 1 and "SIN_OPERATIVIDAD" in groups:
                            nulo = groups.pop("SIN_OPERATIVIDAD")
                            groups[next(iter(groups))].extend(nulo)
                        for operativity_key, group in groups.items():
                            crear.crear(
                                RHInspectorCotizarIn(
                                    cip=cip,
                                    periodo=period[0],
                                    mes=period[1],
                                    # Se pasan dicts y no instancias: al anidar
                                    # una instancia en el payload, Pydantic la
                                    # reconstruye y marca TODOS sus campos como
                                    # enviados, incluido ``expediente``. El flujo
                                    # interpreta ese campo vacio como "limpiar" y
                                    # borraria el expediente de la liquidacion.
                                    items=[
                                        {
                                            "liquidacion_categoria_visitas_id": str(lcv.id),
                                            "cantidad_visitas": visitas_mes,
                                        }
                                        for lcv, visitas_mes in group
                                    ],
                                )
                            )
                else:
                    inspector = _dry_run_inspector(cip)
                    operativity_groups = {
                        _resolve_operativity_key(inspector, lcv)
                        for _, lcv, _, visitas_mes in rows
                        if visitas_mes
                    }
                    monthly_receipts += len(operativity_groups - {"SIN_OPERATIVIDAD"}) or 1
                    setup_status = _dry_run_inspector_status(
                        cip, [lcv for _, lcv, _, _ in rows],
                    )
                    if setup_status != "READY":
                        if setup_status.startswith("READY_AFTER_"):
                            outcomes.append([path.name, cip, period[0], period[1], "", setup_status, f"{len(items)} monthly rows"])
                            continue
                        raise CommandError(f"Inspector {cip}: {setup_status}")
                    RHInspectorMensualCotizarFlujo(core).cotizar(payload)
                outcomes.append([
                    path.name, cip, period[0], period[1], "",
                    "READY" if not options["apply"] else "IMPORTED",
                    f"{len(items)} monthly rows",
                ])
            except Exception as exc:
                outcomes.append([path.name, cip, period[0], period[1], "", "REJECTED", str(exc)])

        with report_path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["WORKBOOK", "CIP", "YEAR", "MONTH", "SOURCE_ROW", "STATUS", "DETAIL"])
            writer.writerows(outcomes)
        mapping_path = report_path.with_name(f"{report_path.stem}_equivalencia.csv")
        equivalencia_headers = [
            "WORKBOOK", "CIP", "YEAR", "MONTH", "SOURCE_ROW",
            "EXPEDIENTE_EXCEL", "COMPROBANTE_EXCEL", "PROPIETARIO", "DISTRITO",
            "VISITAS_PROGRAMADAS", "VISITAS_MES", "VISITAS_PREVIAS",
            "TIPO_EMPAIREJAMIENTO", "ESTADO", "MOTIVO",
            "LIQUIDACION_IO_ID", "IO_EXPEDIENTE", "IO_CATEGORIA", "IO_VISITAS_DB",
        ]
        with mapping_path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(equivalencia_headers)
            writer.writerows(mapping_rows)
        pendientes_path = report_path.with_name(f"{report_path.stem}_pendientes.csv")
        with pendientes_path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(equivalencia_headers)
            writer.writerows(pending_rows)
        counts = Counter(row[5] for row in outcomes)
        self.stdout.write(f"Mode: {'APPLY' if options['apply'] else 'DRY-RUN'}")
        self.stdout.write(f"Report: {report_path}")
        self.stdout.write(f"Equivalence report: {mapping_path}")
        self.stdout.write(f"Pending rows report: {pendientes_path}")
        self.stdout.write(f"Pending rows: {len(pending_rows)}")
        self.stdout.write(f"Outcomes: {dict(counts)}")
        self.stdout.write(f"Matched IO rows: {dict(match_counts)}")
        self.stdout.write(f"Matched IO rows with monthly visits: {monthly_rows_ready}")
        self.stdout.write(f"Monthly receipts to create (one per operativity): {monthly_receipts}")
        self.stdout.write(f"Equivalence rows: {len(mapping_rows)}")
