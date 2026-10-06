"""
Validate and optionally repair migrated legacy EDIF RH delegado details.

Legacy RH rule:
    IMPBRUTO = ROUND(LiquidacionGeneral.sub_total / cantidad_detalles_RH, 2)

This command intentionally does NOT use LiquidacionPorcentajeObraDetalle for RH
legacy. Legacy rounded each RH delegado detail directly and did not redistribute
leftover cents.
"""

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from modules.finanzas.domain.models.detalle_honorario_delegado import DetalleHonorarioDelegado
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import LiquidacionEdificacion


CENT = Decimal("0.01")


def _money(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _diff(actual, expected) -> Decimal:
    return abs(_money(actual) - expected)


class Command(BaseCommand):
    help = "Validate/fix migrated legacy EDIF RH delegado details using legacy division."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--numero", type=int, default=None)
        parser.add_argument("--expediente", type=str, default=None)
        parser.add_argument("--tolerance", type=str, default="0.00")
        parser.add_argument("--only-mismatches", action="store_true")
        parser.add_argument("--csv-output", type=str, default=None)
        parser.add_argument(
            "--source-csv",
            type=str,
            default=None,
            help="Optional EDIF legacy CSV to compare DB monetary fields against source-computed fields.",
        )
        parser.add_argument(
            "--validate-sums",
            action="store_true",
            help="Also validate SUM(detalle.imp_bruto) against liquidacion.sub_total.",
        )
        parser.add_argument(
            "--sum-tolerance",
            type=str,
            default="1.00",
            help="Allowed absolute difference for --validate-sums (default: 1.00).",
        )
        parser.add_argument(
            "--validate-balance",
            action="store_true",
            help="Validate each detail: imp_bruto = renta_cip + aporte_codemu + fondo_comun + neto_honorario.",
        )
        parser.add_argument(
            "--balance-tolerance",
            type=str,
            default="0.01",
            help="Allowed absolute difference for --validate-balance (default: 0.01).",
        )
        parser.add_argument(
            "--progress-every",
            type=int,
            default=500,
            help="Print progress every N liquidaciones while processing (default: 500).",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Update existing DetalleHonorarioDelegado rows. Requires --numero or --all.",
        )
        parser.add_argument("--all", action="store_true", help="Allow --fix for all matching rows.")
        parser.add_argument(
            "--repair-shifted-fields",
            action="store_true",
            help="Also repair recoverable shifted field: aporte_codemu <- current fondo_comun.",
        )

    def handle(self, *args, **options):
        tolerance = _money(options["tolerance"])
        sum_tolerance = _money(options["sum_tolerance"])
        balance_tolerance = _money(options["balance_tolerance"])
        fix_mode = bool(options["fix"])
        fix_all = bool(options["all"])
        repair_shifted = bool(options["repair_shifted_fields"])
        validate_sums = bool(options["validate_sums"])
        validate_balance = bool(options["validate_balance"])
        source_csv = Path(options["source_csv"]) if options["source_csv"] else None

        if tolerance < 0:
            raise CommandError("--tolerance must be >= 0")
        if sum_tolerance < 0:
            raise CommandError("--sum-tolerance must be >= 0")
        if balance_tolerance < 0:
            raise CommandError("--balance-tolerance must be >= 0")
        if fix_mode and not options["numero"] and not fix_all:
            raise CommandError("--fix requires --numero or --all")
        if fix_mode and fix_all and options["limit"] is not None:
            raise CommandError("--fix --all cannot be combined with --limit")
        csv_rows_by_numero = self._load_source_csv(source_csv) if source_csv else {}

        qs = (
            LiquidacionEdificacion.objects.filter(liquidacion__legacy=True)
            .select_related("liquidacion")
            .order_by("numero")
        )
        if options["numero"] is not None:
            qs = qs.filter(numero=options["numero"])
        if options["expediente"]:
            qs = qs.filter(liquidacion__expediente__icontains=options["expediente"].strip())
        if options["limit"] is not None:
            if options["limit"] < 1:
                raise CommandError("--limit must be >= 1")
            qs = qs[: options["limit"]]
        total_liquidaciones = len(qs) if hasattr(qs, "__len__") and not hasattr(qs, "count") else qs.count()
        progress_every = int(options["progress_every"] or 0)

        self.stdout.write(self.style.SUCCESS("=== Validating legacy EDIF RH details ==="))
        self.stdout.write("Source: migrated DB only")
        self.stdout.write("Rule: imp_bruto = ROUND(liquidacion.sub_total / RH detail count, 2)")
        self.stdout.write("No cent redistribution. No LiquidacionPorcentajeObraDetalle source.")
        self.stdout.write(f"Tolerance: {tolerance}")
        if validate_sums:
            self.stdout.write(f"Sum tolerance: {sum_tolerance}")
        if validate_balance:
            self.stdout.write(f"Balance tolerance: {balance_tolerance}")
        if source_csv:
            self.stdout.write(f"Source CSV comparison: {source_csv}")
        if fix_mode:
            scope = "ALL" if fix_all else f"numero={options['numero']}"
            self.stdout.write(self.style.WARNING(f"FIX MODE ENABLED - scope: {scope}"))
            if source_csv:
                self.stdout.write(
                    self.style.WARNING(
                        "  will update from source CSV: imp_bruto, renta_cip, aporte_codemu, fondo_comun, neto_honorario"
                    )
                )
            else:
                self.stdout.write(self.style.WARNING("  will update: imp_bruto"))
            if repair_shifted:
                self.stdout.write(self.style.WARNING("  will also update: aporte_codemu <- current fondo_comun"))
                self.stdout.write(self.style.WARNING("  will NOT guess: fondo_comun, neto_honorario"))

        rows = []
        sum_rows = []
        balance_rows = []
        source_rows = []
        checked = ok = mismatches = no_details = invalid = 0
        sum_ok = sum_mismatch = 0
        balance_ok = balance_mismatch = 0
        fixed_imp = fixed_aporte = 0
        fixed_source_fields = 0

        for edificacion in qs:
            checked += 1
            if progress_every > 0 and (checked == 1 or checked % progress_every == 0):
                percent = (Decimal(checked) / Decimal(total_liquidaciones) * Decimal("100")) if total_liquidaciones else Decimal("0")
                self.stdout.write(
                    f"  Progress: {checked}/{total_liquidaciones} liquidaciones ({percent.quantize(Decimal('0.1'))}%)"
                )
            liquidacion = edificacion.liquidacion
            details = list(
                DetalleHonorarioDelegado.objects.filter(
                    recibo_mensual__isnull=True,
                    liquidacion_delegado__liquidacion=liquidacion,
                )
                .select_related(
                    "liquidacion_delegado__delegado__perfil_ingeniero",
                    "liquidacion_delegado__especialidad_revision",
                )
                .order_by("liquidacion_delegado__especialidad_revision__nombre")
            )
            csv_row = csv_rows_by_numero.get(edificacion.numero)

            if not details:
                no_details += 1
                rows.append(self._result_row(edificacion, liquidacion, None, "SIN_DETALLE"))
                continue

            subtotal = _money(liquidacion.sub_total)
            if subtotal <= 0:
                invalid += 1
                for detail in details:
                    rows.append(self._result_row(edificacion, liquidacion, detail, "SUBTOTAL_INVALIDO"))
                continue

            rh_count = len(details)
            expected_bruto = _round_money(subtotal / Decimal(rh_count))
            residual = _round_money(subtotal - (expected_bruto * rh_count))
            actual_sum = _round_money(sum(_money(detail.imp_bruto) for detail in details))
            expected_sum = _round_money(expected_bruto * rh_count)
            sum_diff_vs_subtotal = abs(actual_sum - subtotal)
            sum_diff_vs_legacy = abs(actual_sum - expected_sum)
            if validate_sums:
                sum_status = "OK" if sum_diff_vs_subtotal <= sum_tolerance else "MISMATCH"
                if sum_status == "OK":
                    sum_ok += 1
                else:
                    sum_mismatch += 1
                sum_rows.append(
                    {
                        "status": sum_status,
                        "numero": edificacion.numero,
                        "liquidacion_id": str(liquidacion.id),
                        "expediente": liquidacion.expediente or "",
                        "subtotal": str(subtotal),
                        "rh_detail_count": rh_count,
                        "expected_imp_bruto_legacy": str(expected_bruto),
                        "expected_sum_legacy": str(expected_sum),
                        "actual_sum_imp_bruto": str(actual_sum),
                        "diff_vs_subtotal": str(sum_diff_vs_subtotal),
                        "diff_vs_legacy_sum": str(sum_diff_vs_legacy),
                        "residual_legacy_rounding": str(residual),
                    }
                )

            for detail in details:
                source_expected = None
                source_needs_fix = False
                if validate_balance:
                    components_sum = _round_money(
                        _money(detail.renta_cip)
                        + _money(detail.aporte_codemu)
                        + _money(detail.fondo_comun)
                        + _money(detail.neto_honorario)
                    )
                    balance_diff = abs(_money(detail.imp_bruto) - components_sum)
                    balance_status = "OK" if balance_diff <= balance_tolerance else "MISMATCH"
                    if balance_status == "OK":
                        balance_ok += 1
                    else:
                        balance_mismatch += 1
                    ld = detail.liquidacion_delegado
                    balance_rows.append(
                        {
                            "status": balance_status,
                            "numero": edificacion.numero,
                            "liquidacion_id": str(liquidacion.id),
                            "expediente": liquidacion.expediente or "",
                            "detalle_id": str(detail.id),
                            "especialidad": getattr(ld.especialidad_revision, "nombre", "") or "",
                            "imp_bruto": str(_money(detail.imp_bruto)),
                            "renta_cip": str(_money(detail.renta_cip)),
                            "aporte_codemu": str(_money(detail.aporte_codemu)),
                            "fondo_comun": str(_money(detail.fondo_comun)),
                            "neto_honorario": str(_money(detail.neto_honorario)),
                            "components_sum": str(components_sum),
                            "balance_diff": str(balance_diff),
                        }
                    )

                if csv_row is not None:
                    source_expected = self._source_values_for_detail(csv_row, detail)
                    source_needs_fix = any(
                        _diff(getattr(detail, field_name), expected_value) > tolerance
                        for field_name, expected_value in {
                            "imp_bruto": source_expected["imp_bruto"],
                            "renta_cip": source_expected["renta_cip"],
                            "aporte_codemu": source_expected["aporte_codemu"],
                            "fondo_comun": source_expected["fondo_comun"],
                            "neto_honorario": source_expected["neto_honorario"],
                        }.items()
                    )
                    source_rows.append(
                        self._source_compare_row(edificacion, liquidacion, detail, source_expected)
                    )

                bad_fields = []
                if _diff(detail.imp_bruto, expected_bruto) > tolerance:
                    bad_fields.append("imp_bruto")
                recovered_aporte = _money(detail.fondo_comun)
                if repair_shifted and _diff(detail.aporte_codemu, recovered_aporte) > tolerance:
                    bad_fields.append("aporte_codemu_shifted")

                status = "OK" if not bad_fields else "MISMATCH"
                if status == "OK":
                    ok += 1
                else:
                    mismatches += 1

                rows.append(
                    self._result_row(
                        edificacion,
                        liquidacion,
                        detail,
                        status,
                        rh_count=rh_count,
                        expected_bruto=expected_bruto,
                        residual=residual,
                        bad_fields=",".join(bad_fields),
                    )
                )

                if fix_mode and (bad_fields or source_needs_fix):
                    update_fields = []
                    notes = []
                    if source_expected is not None:
                        source_field_map = {
                            "imp_bruto": source_expected["imp_bruto"],
                            "renta_cip": source_expected["renta_cip"],
                            "aporte_codemu": source_expected["aporte_codemu"],
                            "fondo_comun": source_expected["fondo_comun"],
                            "neto_honorario": source_expected["neto_honorario"],
                        }
                        for field_name, expected_value in source_field_map.items():
                            if _diff(getattr(detail, field_name), expected_value) > tolerance:
                                setattr(detail, field_name, expected_value)
                                update_fields.append(field_name)
                                notes.append(f"{field_name} -> {expected_value}")
                        fixed_source_fields += len(update_fields)
                    elif "imp_bruto" in bad_fields:
                        detail.imp_bruto = expected_bruto
                        update_fields.append("imp_bruto")
                        fixed_imp += 1
                        notes.append(f"imp_bruto -> {expected_bruto}")
                    if source_expected is None and repair_shifted and "aporte_codemu_shifted" in bad_fields:
                        detail.aporte_codemu = recovered_aporte
                        update_fields.append("aporte_codemu")
                        fixed_aporte += 1
                        notes.append(f"aporte_codemu -> {recovered_aporte}")
                    if update_fields:
                        detail.save(update_fields=update_fields)
                        self.stdout.write(self.style.WARNING(f"  Fixed {detail.id}: {', '.join(notes)}"))

        if options["csv_output"]:
            self._write_csv(Path(options["csv_output"]), rows)
            if validate_sums:
                sum_path = Path(options["csv_output"])
                self._write_csv(sum_path.with_name(f"{sum_path.stem}_sumas{sum_path.suffix}"), sum_rows)
            if validate_balance:
                balance_path = Path(options["csv_output"])
                self._write_csv(balance_path.with_name(f"{balance_path.stem}_balance{balance_path.suffix}"), balance_rows)
            if source_csv:
                source_path = Path(options["csv_output"])
                self._write_csv(source_path.with_name(f"{source_path.stem}_source{source_path.suffix}"), source_rows)

        printed = 0
        for row in rows:
            if options["only_mismatches"] and row["status"] == "OK":
                continue
            style = self.style.SUCCESS if row["status"] == "OK" else self.style.ERROR
            if row["status"] not in {"OK", "MISMATCH"}:
                style = self.style.WARNING
            self.stdout.write(style(self._format_row(row)))
            printed += 1

        if validate_sums:
            self.stdout.write(self.style.SUCCESS("\n=== Sum Validation ==="))
            for row in sum_rows:
                if options["only_mismatches"] and row["status"] == "OK":
                    continue
                style = self.style.SUCCESS if row["status"] == "OK" else self.style.ERROR
                self.stdout.write(
                    style(
                        f"SUM {row['status']} numero={row['numero']} exp={row['expediente']} "
                        f"subtotal={row['subtotal']} sum_imp={row['actual_sum_imp_bruto']} "
                        f"diff={row['diff_vs_subtotal']} tol={sum_tolerance}"
                    )
                )

        if validate_balance:
            self.stdout.write(self.style.SUCCESS("\n=== Balance Validation ==="))
            for row in balance_rows:
                if options["only_mismatches"] and row["status"] == "OK":
                    continue
                style = self.style.SUCCESS if row["status"] == "OK" else self.style.ERROR
                self.stdout.write(
                    style(
                        f"BALANCE {row['status']} numero={row['numero']} exp={row['expediente']} "
                        f"esp={row['especialidad']} imp={row['imp_bruto']} "
                        f"componentes={row['components_sum']} diff={row['balance_diff']} "
                        f"tol={balance_tolerance}"
                    )
                )

        if source_csv:
            source_mismatch = sum(1 for row in source_rows if row["status"] == "MISMATCH")
            source_ok = sum(1 for row in source_rows if row["status"] == "OK")
            self.stdout.write(self.style.SUCCESS("\n=== Source CSV Validation ==="))
            self.stdout.write(f"Source rows OK:              {source_ok}")
            self.stdout.write(f"Source rows mismatch:        {source_mismatch}")

        self.stdout.write(self.style.SUCCESS("\n=== Summary ==="))
        self.stdout.write(f"Liquidaciones EDIF revisadas: {checked}")
        self.stdout.write(f"Detalle rows OK:              {ok}")
        self.stdout.write(f"Detalle rows mismatch:        {mismatches}")
        self.stdout.write(f"Liquidaciones sin detalle:    {no_details}")
        self.stdout.write(f"Liquidaciones invalidas:      {invalid}")
        self.stdout.write(f"Filas impresas:               {printed}")
        if validate_sums:
            self.stdout.write(f"Suma liquidaciones OK:        {sum_ok}")
            self.stdout.write(f"Suma liquidaciones mismatch:  {sum_mismatch}")
        if validate_balance:
            self.stdout.write(f"Balance detalle OK:           {balance_ok}")
            self.stdout.write(f"Balance detalle mismatch:     {balance_mismatch}")
        if fix_mode:
            self.stdout.write(self.style.WARNING(f"imp_bruto fixed:              {fixed_imp}"))
            if source_csv:
                self.stdout.write(self.style.WARNING(f"source CSV fields fixed:      {fixed_source_fields}"))
            if repair_shifted:
                self.stdout.write(self.style.WARNING(f"aporte_codemu fixed:          {fixed_aporte}"))
        if options["csv_output"]:
            self.stdout.write(f"CSV:                          {options['csv_output']}")
            if validate_sums:
                sum_path = Path(options["csv_output"])
                self.stdout.write(f"CSV sumas:                    {sum_path.with_name(f'{sum_path.stem}_sumas{sum_path.suffix}')} ")
            if validate_balance:
                balance_path = Path(options["csv_output"])
                self.stdout.write(f"CSV balance:                  {balance_path.with_name(f'{balance_path.stem}_balance{balance_path.suffix}')} ")
            if source_csv:
                source_path = Path(options["csv_output"])
                self.stdout.write(f"CSV source:                   {source_path.with_name(f'{source_path.stem}_source{source_path.suffix}')} ")

    def _result_row(self, edificacion, liquidacion, detail, status, rh_count="", expected_bruto="", residual="", bad_fields=""):
        delegado = especialidad = ""
        if detail is not None:
            ld = detail.liquidacion_delegado
            delegado = getattr(getattr(ld.delegado, "perfil_ingeniero", None), "nombre_completo", "") or ""
            especialidad = getattr(ld.especialidad_revision, "nombre", "") or ""
        return {
            "status": status,
            "numero": edificacion.numero,
            "liquidacion_id": str(liquidacion.id),
            "expediente": liquidacion.expediente or "",
            "fecha_registro": liquidacion.fecha_registro.date().isoformat() if liquidacion.fecha_registro else "",
            "subtotal": str(_money(liquidacion.sub_total)),
            "rh_detail_count": rh_count,
            "expected_imp_bruto_legacy": str(expected_bruto or ""),
            "residual_legacy_rounding": str(residual or ""),
            "detalle_id": str(detail.id) if detail else "",
            "especialidad": especialidad,
            "delegado": delegado,
            "actual_imp_bruto": str(_money(detail.imp_bruto)) if detail else "",
            "actual_renta_cip": str(_money(detail.renta_cip)) if detail else "",
            "actual_aporte_codemu": str(_money(detail.aporte_codemu)) if detail else "",
            "actual_fondo_comun": str(_money(detail.fondo_comun)) if detail else "",
            "actual_neto_honorario": str(_money(detail.neto_honorario)) if detail else "",
            "bad_fields": bad_fields,
        }

    def _format_row(self, row):
        base = (
            f"{row['status']} numero={row['numero']} exp={row['expediente']} "
            f"rh_count={row['rh_detail_count']} esp={row['especialidad']} bad={row['bad_fields'] or '-'}"
        )
        if row["status"] == "MISMATCH":
            return f"{base} | bruto {row['actual_imp_bruto']}->{row['expected_imp_bruto_legacy']}"
        return base

    def _write_csv(self, path: Path, rows: list[dict]):
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)

    def _load_source_csv(self, path: Path) -> dict[int, dict]:
        if not path.exists():
            raise CommandError(f"--source-csv not found: {path}")
        with path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file, delimiter=";")
            header = next(reader, None)
            if not header:
                raise CommandError(f"--source-csv has no header: {path}")
            rows = {}
            for raw in reader:
                if not raw:
                    continue
                try:
                    numero = int(float(str(raw[0]).strip()))
                except (ValueError, TypeError):
                    continue
                rows[numero] = {"raw": raw, "header": header}
        return rows

    def _source_values_for_detail(self, csv_row: dict, detail: DetalleHonorarioDelegado) -> dict:
        raw = csv_row["raw"]
        # EDIF_ALL.csv monetary columns after DELEGADO1..4.
        values = {
            "imp_bruto": _money(raw[26] if len(raw) > 26 else None),
            "renta_cip": _money(raw[72] if len(raw) > 72 else None),
            "aporte_codemu": _money(raw[27] if len(raw) > 27 else None),
            "fondo_comun": _money(raw[28] if len(raw) > 28 else None),
            "neto_honorario": _money(raw[31] if len(raw) > 31 else None),
        }
        return values

    def _source_compare_row(self, edificacion, liquidacion, detail, expected: dict) -> dict:
        ld = detail.liquidacion_delegado
        actual = {
            "imp_bruto": _money(detail.imp_bruto),
            "renta_cip": _money(detail.renta_cip),
            "aporte_codemu": _money(detail.aporte_codemu),
            "fondo_comun": _money(detail.fondo_comun),
            "neto_honorario": _money(detail.neto_honorario),
        }
        diffs = {name: abs(actual[name] - expected[name]) for name in actual}
        bad_fields = [name for name, value in diffs.items() if value > Decimal("0.00")]
        return {
            "status": "OK" if not bad_fields else "MISMATCH",
            "numero": edificacion.numero,
            "liquidacion_id": str(liquidacion.id),
            "expediente": liquidacion.expediente or "",
            "detalle_id": str(detail.id),
            "especialidad": getattr(ld.especialidad_revision, "nombre", "") or "",
            "delegado": getattr(getattr(ld.delegado, "perfil_ingeniero", None), "nombre_completo", "") or "",
            "actual_imp_bruto": str(actual["imp_bruto"]),
            "source_imp_bruto": str(expected["imp_bruto"]),
            "diff_imp_bruto": str(diffs["imp_bruto"]),
            "actual_renta_cip": str(actual["renta_cip"]),
            "source_renta_cip": str(expected["renta_cip"]),
            "diff_renta_cip": str(diffs["renta_cip"]),
            "actual_aporte_codemu": str(actual["aporte_codemu"]),
            "source_aporte_codemu": str(expected["aporte_codemu"]),
            "diff_aporte_codemu": str(diffs["aporte_codemu"]),
            "actual_fondo_comun": str(actual["fondo_comun"]),
            "source_fondo_comun": str(expected["fondo_comun"]),
            "diff_fondo_comun": str(diffs["fondo_comun"]),
            "actual_neto_honorario": str(actual["neto_honorario"]),
            "source_neto_honorario": str(expected["neto_honorario"]),
            "diff_neto_honorario": str(diffs["neto_honorario"]),
            "bad_fields": ",".join(bad_fields),
        }
