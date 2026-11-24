"""Repair H-based PO allocations for selected-specialty legacy modifications.

The legacy import split the amount of a *modificación de licencia* across the
universe of H enabled specialties (H=3/H=4) even when only ONE specialty was
actually charged.  This command regularises those records into the
``TOTAL_EXPLICITO_SELECCIONADAS`` strategy: the historical amounts are kept
verbatim and the subtotal is distributed among the SELECTED specialties only.

Guarantees:

- **dry-run by default** (``--apply`` is required to write) and an audited CSV
  is always produced (``--csv-output`` is required);
- **idempotent**: re-running finds nothing left to fix;
- the authoritative amounts of the parent (``LiquidacionGeneral.sub_total`` and
  ``LiquidacionGeneral.total``) are NEVER touched;
- H (habilitadas) is never written: ``cantidad_especialidades_habilitadas``
  ends up NULL;
- the selected specialty and its tariff are recorded as REFERENCE (parent
  ``porcentaje_tarifa`` + detail ``porcentaje_aplicado`` / ``tarifa_aplicada``).
"""

import csv
import re
import unicodedata
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.liquidaciones.domain.constants import EstrategiaCotizacionPO
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorcentajeObra,
)


H_STRATEGIES = {
    "TARIFA_HABILITADAS_PARTICIPANTES",
    "TOTAL_EXPLICITO",
}
NORMAL_SELECCIONADAS = "NORMAL_SELECCIONADAS"
TOTAL_EXPLICITO_SELECCIONADAS = EstrategiaCotizacionPO.TOTAL_EXPLICITO_SELECCIONADAS


def normalize_label(value: str | None) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_accents = "".join(
        character for character in normalized if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", without_accents.lower()).strip()


def is_modificacion_licencia(value: str | None) -> bool:
    """Match legacy modification labels while never reclassifying reintegros."""
    label = normalize_label(value)
    if "reintegro" in label:
        return False
    return "modificacion" in label or "modif" in label


def _tarifa_vigente_por_fecha(fecha) -> TarifaPorcentajeObra | None:
    """Resuelve la tarifa vigente de Edificaciones en la fecha del registro.

    La tarifa es sólo REFERENCIA (no interviene en el importe): si no se puede
    resolver, el comando sigue funcionando y lo registra en el CSV.
    """
    from modules.liquidaciones.domain.constants import TipoLiquidacion
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )

    bases = TarifaLiquidacionBase.objects.vigentes(fecha=fecha).filter(
        tipo_liquidacion__codigo=TipoLiquidacion.EDIFICACION
    )
    return (
        TarifaPorcentajeObra.objects.filter(tarifa_base__in=bases)
        .select_related("tarifa_base")
        .first()
    )


class Command(BaseCommand):
    help = (
        "Repair legacy EDIF modification PO details split by H=3/H=4 into the "
        "TOTAL_EXPLICITO_SELECCIONADAS strategy. Preserves historical parent "
        "amounts; dry-run by default."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--csv-output", required=True)

    def handle(self, *args, **options):
        dry_run = not options["apply"]
        rows = []
        updates = []
        parents = (
            LiquidacionEdificacion.objects.filter(liquidacion__legacy=True)
            .select_related("liquidacion", "liquidacion__liquidacion_porcentaje_obra")
            .prefetch_related("liquidacion__liquidacion_porcentaje_obra__detalles")
            .order_by("numero")
        )

        for edificacion in parents:
            liquidacion = edificacion.liquidacion
            if not is_modificacion_licencia(liquidacion.denominacion_de_proyecto):
                continue

            porcentaje = liquidacion.liquidacion_porcentaje_obra
            detalles = list(porcentaje.detalles.all())
            if porcentaje.estrategia_cotizacion not in H_STRATEGIES:
                continue

            row = {
                "numero": edificacion.numero,
                "expediente": liquidacion.expediente or "",
                "fecha_registro": liquidacion.fecha_registro.date().isoformat(),
                "proyecto": liquidacion.denominacion_de_proyecto or "",
                "estrategia_anterior": porcentaje.estrategia_cotizacion,
                "estrategia_propuesta": TOTAL_EXPLICITO_SELECCIONADAS,
                "h_anterior": porcentaje.cantidad_especialidades_habilitadas or "",
                "h_propuesta": "",
                "subtotal_historico": liquidacion.sub_total,
                "total_historico": liquidacion.total,
                "detalle_count": len(detalles),
                "especialidad": detalles[0].especialidad.nombre if len(detalles) == 1 else "",
                "detalle_subtotal_anterior": detalles[0].subtotal if len(detalles) == 1 else "",
                "detalle_subtotal_propuesto": liquidacion.sub_total if len(detalles) == 1 else "",
                "porcentaje_tarifa_propuesto": "",
                "tarifa_aplicada_id_propuesta": "",
                "status": "",
            }

            if len(detalles) != 1:
                row["status"] = "SKIPPED_AMBIGUOUS_DETAIL_COUNT"
                rows.append(row)
                continue
            if porcentaje.cantidad_especialidades_habilitadas not in (3, 4):
                row["status"] = "SKIPPED_UNEXPECTED_H"
                rows.append(row)
                continue
            if liquidacion.sub_total is None:
                row["status"] = "SKIPPED_MISSING_PARENT_SUBTOTAL"
                rows.append(row)
                continue
            if liquidacion.total is None:
                row["status"] = "SKIPPED_MISSING_PARENT_TOTAL"
                rows.append(row)
                continue

            detail = detalles[0]
            # La tarifa vigente en la fecha del registro es sólo REFERENCIA.
            tarifa = _tarifa_vigente_por_fecha(liquidacion.fecha_registro.date())
            row["porcentaje_tarifa_propuesto"] = (
                tarifa.porcentaje_liquidacion if tarifa is not None else ""
            )
            row["tarifa_aplicada_id_propuesta"] = str(tarifa.id) if tarifa is not None else ""

            row["status"] = "APPLIED" if options["apply"] else "PLANNED"
            rows.append(row)
            updates.append((porcentaje, detail, liquidacion, tarifa))

        if options["apply"]:
            with transaction.atomic():
                for porcentaje, detail, liquidacion, tarifa in updates:
                    # ── Padre: importe autoritativo + referencia, H siempre NULL ──
                    porcentaje.estrategia_cotizacion = TOTAL_EXPLICITO_SELECCIONADAS
                    porcentaje.cantidad_especialidades_habilitadas = None
                    porcentaje.porcentaje_liquidacion = None
                    porcentaje.total_explicito = liquidacion.total
                    porcentaje.porcentaje_tarifa = (
                        tarifa.porcentaje_liquidacion if tarifa is not None else None
                    )
                    if tarifa is not None:
                        porcentaje.tarifa_aplicada = tarifa
                    porcentaje.save(
                        update_fields=[
                            "estrategia_cotizacion",
                            "cantidad_especialidades_habilitadas",
                            "porcentaje_liquidacion",
                            "total_explicito",
                            "porcentaje_tarifa",
                            "tarifa_aplicada",
                            "updated_at",
                        ]
                    )
                    # ── Detalle: el importe histórico completo (sólo la
                    #    especialidad seleccionada) + la tasa como REFERENCIA ──
                    detail.subtotal = liquidacion.sub_total
                    detail.importe_parcial = liquidacion.sub_total
                    detail.ajuste_redondeo = Decimal("0.00")
                    if tarifa is not None:
                        detail.tarifa_aplicada = tarifa
                    if tarifa is not None and detail.porcentaje_aplicado is None:
                        detail.porcentaje_aplicado = tarifa.porcentaje_liquidacion
                    detail.save(
                        update_fields=[
                            "subtotal",
                            "importe_parcial",
                            "ajuste_redondeo",
                            "tarifa_aplicada",
                            "porcentaje_aplicado",
                            "updated_at",
                        ]
                    )
                    # NUNCA se tocan `liquidacion.sub_total` ni `liquidacion.total`:
                    # son los importes autoritativos de la liquidación.

        output = Path(options["csv_output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(rows[0]) if rows else ["status"]
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        action = "corrected" if options["apply"] else "planned"
        self.stdout.write(self.style.SUCCESS(f"Modification PO records {action}: {len(updates)}"))
        self.stdout.write(f"CSV: {output}")
