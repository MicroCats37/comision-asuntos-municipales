"""Audit post-cutover legacy EDIF RH details without changing persisted data."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from modules.finanzas.domain.models.detalle_honorario_delegado import DetalleHonorarioDelegado
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)

from .legacy_edif import money, money_diff, round_money


CUTOVER_DATE = date(2026, 5, 1)
H3 = 3
UNIT_RATE = Decimal("0.0005")
H3_RATE = Decimal("0.0015")
MONEY_TOLERANCE = Decimal("0.01")
RH_FIELDS = ("imp_bruto", "renta_cip", "aporte_codemu", "fondo_comun", "neto_honorario")


def expected_rh_values(subtotal, divisor: int) -> dict[str, Decimal]:
    bruto = round_money(money(subtotal) / Decimal(divisor))
    return {
        "imp_bruto": bruto,
        "renta_cip": round_money(bruto * Decimal("0.25")),
        "aporte_codemu": round_money(bruto * Decimal("0.05")),
        "fondo_comun": round_money(bruto * Decimal("0.10")),
        "neto_honorario": round_money(bruto * Decimal("0.60")),
    }


def rh_matches(details, expected: dict[str, Decimal], tolerance: Decimal) -> bool:
    return bool(details) and all(
        money_diff(getattr(detail, field), expected[field]) <= tolerance
        for detail in details
        for field in RH_FIELDS
    )


def bruto_matches(details, expected: dict[str, Decimal], tolerance: Decimal) -> bool:
    return bool(details) and all(
        money_diff(detail.imp_bruto, expected["imp_bruto"]) <= tolerance
        for detail in details
    )


def classify_rh(details, subtotal, tolerance: Decimal) -> tuple[str, dict[str, Decimal]]:
    expected_h3 = expected_rh_values(subtotal, H3)
    if not details:
        return "RH_SIN_DETALLE", expected_h3
    if len(details) == H3 and rh_matches(details, expected_h3, tolerance):
        return "RH_CORRECTO", expected_h3
    if bruto_matches(details, expected_rh_values(subtotal, 4), tolerance):
        return "RH_DIVIDIDO_4", expected_h3
    if len(details) != H3:
        return "RH_CANTIDAD_INESPERADA", expected_h3
    return "RH_DISCREPANTE", expected_h3


def classify_po(porcentaje) -> str:
    if (
        porcentaje.porcentaje_liquidacion == H3_RATE
        and (
            porcentaje.cantidad_especialidades_habilitadas == H3
            or porcentaje.cantidad_especialidades_habilitadas is None
        )
        and (porcentaje.porcentaje_tarifa in (UNIT_RATE, None))
    ):
        return "PO_CORRECTO"
    return "PO_DISCREPANTE"


class Command(BaseCommand):
    help = "Audita RH legacy EDIF H=3 posterior al corte sin modificar datos."

    def add_arguments(self, parser):
        parser.add_argument("--numero", type=int, default=None)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--fecha-desde", type=str, default=CUTOVER_DATE.isoformat())
        parser.add_argument("--tolerance", type=str, default=str(MONEY_TOLERANCE))
        parser.add_argument("--csv-output", type=str, default=None)
        parser.add_argument("--only-mismatches", action="store_true")

    def handle(self, *args, **options):
        try:
            fecha_desde = date.fromisoformat(options["fecha_desde"])
        except ValueError as exc:
            raise CommandError("--fecha-desde must use YYYY-MM-DD") from exc
        tolerance = money(options["tolerance"])
        if tolerance < 0:
            raise CommandError("--tolerance must be >= 0")
        if options["limit"] is not None and options["limit"] < 1:
            raise CommandError("--limit must be >= 1")

        qs = (
            LiquidacionEdificacion.objects.filter(
                liquidacion__legacy=True,
                liquidacion__fecha_registro__date__gte=fecha_desde,
                liquidacion__liquidacion_porcentaje_obra__porcentaje_liquidacion=H3_RATE,
            )
            .select_related("liquidacion", "liquidacion__liquidacion_porcentaje_obra")
            .order_by("numero")
        )
        if options["numero"] is not None:
            qs = qs.filter(numero=options["numero"])
        if options["limit"] is not None:
            qs = qs[: options["limit"]]

        rows = []
        for edificacion in qs:
            liquidacion = edificacion.liquidacion
            porcentaje = liquidacion.liquidacion_porcentaje_obra
            details = list(
                DetalleHonorarioDelegado.objects.filter(
                    recibo_mensual__isnull=True,
                    liquidacion_delegado__liquidacion=liquidacion,
                ).order_by("liquidacion_delegado__especialidad_revision__nombre")
            )
            po_status = classify_po(porcentaje)
            rh_status, expected = classify_rh(details, liquidacion.sub_total, tolerance)
            classification = f"{po_status}+{rh_status}"
            rows.append(
                {
                    "numero": edificacion.numero,
                    "liquidacion_id": str(liquidacion.id),
                    "expediente": liquidacion.expediente or "",
                    "fecha_registro": liquidacion.fecha_registro.date().isoformat(),
                    "subtotal": str(money(liquidacion.sub_total)),
                    "po_status": po_status,
                    "rh_status": rh_status,
                    "classification": classification,
                    "rh_detail_count": len(details),
                    "expected_imp_bruto_h3": str(expected["imp_bruto"]),
                    "expected_renta_cip_h3": str(expected["renta_cip"]),
                    "expected_aporte_codemu_h3": str(expected["aporte_codemu"]),
                    "expected_fondo_comun_h3": str(expected["fondo_comun"]),
                    "expected_neto_honorario_h3": str(expected["neto_honorario"]),
                    "estrategia_cotizacion": porcentaje.estrategia_cotizacion,
                    "cantidad_habilitadas": porcentaje.cantidad_especialidades_habilitadas,
                    "porcentaje_tarifa": str(porcentaje.porcentaje_tarifa),
                    "porcentaje_liquidacion": str(porcentaje.porcentaje_liquidacion),
                }
            )

        if options["csv_output"]:
            output = Path(options["csv_output"])
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=list(rows[0]) if rows else self._fieldnames())
                writer.writeheader()
                writer.writerows(rows)

        printed = 0
        for row in rows:
            if options["only_mismatches"] and row["classification"] == "PO_CORRECTO+RH_CORRECTO":
                continue
            style = self.style.SUCCESS if row["classification"] == "PO_CORRECTO+RH_CORRECTO" else self.style.WARNING
            self.stdout.write(style(f"{row['classification']} numero={row['numero']} subtotal={row['subtotal']}"))
            printed += 1

        rh_divided_4 = sum(row["rh_status"] == "RH_DIVIDIDO_4" for row in rows)
        self.stdout.write(self.style.SUCCESS("=== EDIF H=3 RH reconciliation ==="))
        self.stdout.write(f"Liquidaciones revisadas: {len(rows)}")
        self.stdout.write(f"RH dividido entre 4:    {rh_divided_4}")
        self.stdout.write(f"Filas impresas:         {printed}")
        if options["csv_output"]:
            self.stdout.write(f"CSV:                    {options['csv_output']}")

    @staticmethod
    def _fieldnames():
        return [
            "numero", "liquidacion_id", "expediente", "fecha_registro", "subtotal", "po_status",
            "rh_status", "classification", "rh_detail_count", "expected_imp_bruto_h3",
            "expected_renta_cip_h3", "expected_aporte_codemu_h3", "expected_fondo_comun_h3",
            "expected_neto_honorario_h3", "estrategia_cotizacion", "cantidad_habilitadas",
            "porcentaje_tarifa", "porcentaje_liquidacion",
        ]
