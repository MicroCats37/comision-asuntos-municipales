"""
Validate and optionally repair migrated legacy EDIF RH delegado details.

Legacy RH rule:
    IMPBRUTO = ROUND(LiquidacionGeneral.sub_total / cantidad_detalles_RH, 2)

This command intentionally does NOT use LiquidacionPorcentajeObraDetalle for RH
legacy. Legacy rounded each RH delegado detail directly and did not redistribute
leftover cents.

Curation mode (--curate-delegado):
    Backfill null fields on LiquidacionDelegado from EDIF_ALL.csv DELEGADO slots.
"""

from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from modules.finanzas.domain.models.detalle_honorario_delegado import DetalleHonorarioDelegado
from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)

from .legacy_edif import (
    curation_report_header,
    curate_record,
    extract_slot_fields,
    money,
    round_money,
    money_diff,
    load_source_csv,
    write_csv as write_csv_file,
    format_result_row,
    SLOT_SPECIALTY_DB_MAP,
)
from .legacy_edif import extract_source_values, build_source_compare_row


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
        parser.add_argument(
            "--curate-delegado",
            action="store_true",
            help=(
                "Curation mode: backfill null fields on LiquidacionDelegado from "
                "EDIF_ALL.csv DELEGADO slots (PERIODO, MES, FECHAPRES, FECHAREVI, "
                "NROORDEN, DICTAMEN). Writes CSV report. Use --fix to apply changes."
            ),
        )

    def handle(self, *args, **options):
        tolerance = money(options["tolerance"])
        sum_tolerance = money(options["sum_tolerance"])
        balance_tolerance = money(options["balance_tolerance"])
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
        try:
            csv_rows_by_numero = load_source_csv(source_csv) if source_csv else {}
        except (FileNotFoundError, ValueError) as e:
            raise CommandError(str(e))

        # ── Curation mode ──────────────────────────────────────────────────────────
        curate_mode = bool(options.get("curate_delegado"))
        if curate_mode:
            if not source_csv:
                raise CommandError("--curate-delegado requires --source-csv")
            self._handle_curate_delegado(
                source_csv=source_csv,
                csv_rows_by_numero=csv_rows_by_numero,
                options=options,
            )
            return

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

            subtotal = money(liquidacion.sub_total)
            if subtotal <= 0:
                invalid += 1
                for detail in details:
                    rows.append(self._result_row(edificacion, liquidacion, detail, "SUBTOTAL_INVALIDO"))
                continue

            rh_count = len(details)
            expected_bruto = round_money(subtotal / Decimal(rh_count))
            residual = round_money(subtotal - (expected_bruto * rh_count))
            actual_sum = round_money(sum(money(detail.imp_bruto) for detail in details))
            expected_sum = round_money(expected_bruto * rh_count)
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
                    components_sum = round_money(
                        money(detail.renta_cip)
                        + money(detail.aporte_codemu)
                        + money(detail.fondo_comun)
                        + money(detail.neto_honorario)
                    )
                    balance_diff = abs(money(detail.imp_bruto) - components_sum)
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
                            "imp_bruto": str(money(detail.imp_bruto)),
                            "renta_cip": str(money(detail.renta_cip)),
                            "aporte_codemu": str(money(detail.aporte_codemu)),
                            "fondo_comun": str(money(detail.fondo_comun)),
                            "neto_honorario": str(money(detail.neto_honorario)),
                            "components_sum": str(components_sum),
                            "balance_diff": str(balance_diff),
                        }
                    )

                if csv_row is not None:
                    source_expected = extract_source_values(csv_row)
                    source_needs_fix = any(
                        money_diff(getattr(detail, field_name), expected_value) > tolerance
                        for field_name, expected_value in {
                            "imp_bruto": source_expected["imp_bruto"],
                            "renta_cip": source_expected["renta_cip"],
                            "aporte_codemu": source_expected["aporte_codemu"],
                            "fondo_comun": source_expected["fondo_comun"],
                            "neto_honorario": source_expected["neto_honorario"],
                        }.items()
                    )
                    source_rows.append(
                        build_source_compare_row(edificacion, liquidacion, detail, source_expected)
                    )

                bad_fields = []
                if money_diff(detail.imp_bruto, expected_bruto) > tolerance:
                    bad_fields.append("imp_bruto")
                recovered_aporte = money(detail.fondo_comun)
                if repair_shifted and money_diff(detail.aporte_codemu, recovered_aporte) > tolerance:
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
                            if money_diff(getattr(detail, field_name), expected_value) > tolerance:
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
            write_csv_file(Path(options["csv_output"]), rows)
            if validate_sums:
                sum_path = Path(options["csv_output"])
                write_csv_file(sum_path.with_name(f"{sum_path.stem}_sumas{sum_path.suffix}"), sum_rows)
            if validate_balance:
                balance_path = Path(options["csv_output"])
                write_csv_file(balance_path.with_name(f"{balance_path.stem}_balance{balance_path.suffix}"), balance_rows)
            if source_csv:
                source_path = Path(options["csv_output"])
                write_csv_file(source_path.with_name(f"{source_path.stem}_source{source_path.suffix}"), source_rows)

        printed = 0
        for row in rows:
            if options["only_mismatches"] and row["status"] == "OK":
                continue
            style = self.style.SUCCESS if row["status"] == "OK" else self.style.ERROR
            if row["status"] not in {"OK", "MISMATCH"}:
                style = self.style.WARNING
            self.stdout.write(style(format_result_row(row)))
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
            "subtotal": str(money(liquidacion.sub_total)),
            "rh_detail_count": rh_count,
            "expected_imp_bruto_legacy": str(expected_bruto or ""),
            "residual_legacy_rounding": str(residual or ""),
            "detalle_id": str(detail.id) if detail else "",
            "especialidad": especialidad,
            "delegado": delegado,
            "actual_imp_bruto": str(money(detail.imp_bruto)) if detail else "",
            "actual_renta_cip": str(money(detail.renta_cip)) if detail else "",
            "actual_aporte_codemu": str(money(detail.aporte_codemu)) if detail else "",
            "actual_fondo_comun": str(money(detail.fondo_comun)) if detail else "",
            "actual_neto_honorario": str(money(detail.neto_honorario)) if detail else "",
            "bad_fields": bad_fields,
        }

    # ── Curation mode ────────────────────────────────────────────────────────────

    def _handle_curate_delegado(self, source_csv, csv_rows_by_numero, options):
        """
        Curation mode: backfill null fields on LiquidacionDelegado from EDIF_ALL.csv.

        Curation rules:
            FILLED   — DB is null/empty and CSV has a valid parsed value
            CONFLICT — DB has a value and CSV has a different value (never overwrites)
            SKIP     — DB has a value matching CSV, or both are null
        """
        fix_mode = bool(options.get("fix"))
        limit = options.get("limit")
        numero_filter = options.get("numero")
        expediente_filter = options.get("expediente")
        csv_output = options.get("csv_output")
        progress_every = int(options.get("progress_every", 500) or 0)

        if not fix_mode:
            self.stdout.write(self.style.WARNING("=== CURATION DRY RUN (no --fix passed) ==="))
        else:
            self.stdout.write(self.style.WARNING("=== CURATION FIX MODE ==="))

        # Build slot_num -> especialidad_nombre map (DB canonical names)
        slot_to_specialty = {slot: name for slot, name in SLOT_SPECIALTY_DB_MAP.items()}
        specialty_to_slot = {name: slot for slot, name in SLOT_SPECIALTY_DB_MAP.items()}

        # Pre-fetch EspecialidadRevision objects by nombre
        specialty_qs = EspecialidadRevision.objects.filter(
            nombre__in=list(slot_to_specialty.values())
        )
        specialty_by_nombre = {s.nombre: s for s in specialty_qs}

        # Queryset
        qs = (
            LiquidacionEdificacion.objects.filter(liquidacion__legacy=True)
            .select_related("liquidacion")
            .order_by("numero")
        )
        if numero_filter is not None:
            qs = qs.filter(numero=numero_filter)
        if expediente_filter:
            qs = qs.filter(liquidacion__expediente__icontains=expediente_filter.strip())
        if limit is not None:
            if limit < 1:
                raise CommandError("--limit must be >= 1")
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(f"Source CSV: {source_csv}")
        self.stdout.write(f"Total liquidaciones to process: {total}")
        self.stdout.write(f"Fix mode: {'YES' if fix_mode else 'NO (dry run)'}")

        # Collect all curation report rows
        curation_rows = []
        checked = curated = conflicts = skipped = 0

        for edificacion in qs:
            checked += 1
            if progress_every > 0 and (checked == 1 or checked % progress_every == 0):
                pct = (Decimal(checked) / Decimal(total) * Decimal("100")) if total else Decimal("0")
                self.stdout.write(
                    f"  Progress: {checked}/{total} ({pct.quantize(Decimal('0.1'))}%)"
                )

            liquidacion = edificacion.liquidacion
            csv_row = csv_rows_by_numero.get(edificacion.numero)

            if csv_row is None:
                skipped += 1
                continue

            # Get all LiquidacionDelegado for this liquidacion
            ld_records = list(
                LiquidacionDelegado.objects.filter(liquidacion=liquidacion)
                .select_related("delegado__perfil_ingeniero", "especialidad_revision")
            )

            if not ld_records:
                skipped += 1
                continue

            raw = csv_row["raw"]

            for ld in ld_records:
                esp_nombre = getattr(ld.especialidad_revision, "nombre", "") or ""
                slot_num = specialty_to_slot.get(esp_nombre)
                if slot_num is None:
                    # Specialty not in our slot map — skip
                    skipped += 1
                    continue

                slot_fields = extract_slot_fields(raw, slot_num)
                slot_fields["slot_num"] = slot_num

                # Run curation (dry_run=not fix_mode)
                results = curate_record(ld, slot_fields, edificacion.numero, dry_run=not fix_mode)

                # Count actions
                for r in results:
                    curation_rows.append(r)
                    if r["action"] == "FILLED":
                        curated += 1
                    elif r["action"] == "CONFLICT":
                        conflicts += 1
                    else:
                        skipped += 1

        # Write CSV report
        if csv_output:
            output_path = Path(csv_output)
            write_csv_file(output_path, curation_rows)
            self.stdout.write(f"CSV report: {output_path}")

        # Console output
        printed = 0
        for r in curation_rows:
            if options.get("only_mismatches") and r["action"] not in ("FILLED", "CONFLICT"):
                continue
            if r["action"] == "FILLED":
                style = self.style.SUCCESS
            elif r["action"] == "CONFLICT":
                style = self.style.ERROR
            else:
                style = self.style.WARNING
            self.stdout.write(
                style(
                    f"{r['action']} numero={r['numero']} slot={r['slot']} "
                    f"delegado={r['delegado']} field={r['field']} "
                    f"db={r['db_value'] or '(null)'} -> src={r['source_value'] or '(null)'}"
                )
            )
            printed += 1

        self.stdout.write(self.style.SUCCESS("\n=== Curation Summary ==="))
        self.stdout.write(f"Liquidaciones checked:      {checked}")
        self.stdout.write(f"Fields FILLED:              {curated}")
        self.stdout.write(f"Fields CONFLICT:            {conflicts}")
        self.stdout.write(f"Fields SKIPPED:             {skipped}")
        self.stdout.write(f"Total field actions:        {len(curation_rows)}")
        if csv_output:
            self.stdout.write(f"CSV report:                 {csv_output}")
