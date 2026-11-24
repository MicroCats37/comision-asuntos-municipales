"""Repair comprobantes attached to current liquidaciones by legacy number collisions."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.liquidaciones.models import (
    LiquidacionComprobante,
    LiquidacionEdificacion,
    LiquidacionInspeccionObra,
)


@dataclass(frozen=True)
class Collision:
    tipo: str
    numero: int
    liquidacion_id: str
    comprobante_id: str
    legacy_serie: str
    legacy_numero: str
    legacy_fecha: date | None
    legacy_monto: Decimal


def _c(
    tipo: str,
    numero: int,
    liquidacion_id: str,
    comprobante_id: str,
    serie: str,
    comprobante_numero: str,
    fecha: str | None,
    monto: str,
) -> Collision:
    return Collision(
        tipo=tipo,
        numero=numero,
        liquidacion_id=liquidacion_id,
        comprobante_id=comprobante_id,
        legacy_serie=serie,
        legacy_numero=comprobante_numero,
        legacy_fecha=date.fromisoformat(fecha) if fecha else None,
        legacy_monto=Decimal(monto),
    )


# Fuente de verdad: cam_db_backup_20261123_043800.dump. En el backup ninguna de
# estas 31 liquidaciones no legacy tenía comprobantes. Los IDs y la identidad
# legacy permiten borrar solo la contaminación que aún no fue corregida a mano.
COLLISIONS = (
    _c(
        "IO",
        16,
        "ef5d75a8-2801-4257-9512-d3769576f17e",
        "1feb2826-f5dd-4055-a3e3-cb5bbe390659",
        "F002",
        "00135467",
        "2012-08-13",
        "775.26",
    ),
    _c(
        "IO",
        18,
        "4f89547d-27d4-4116-a525-8d8d98f34c9e",
        "56438a04-6be5-4155-857c-139c84ba5373",
        "F003",
        "0312230",
        "2009-03-30",
        "337.96",
    ),
    _c(
        "IO",
        21,
        "b90fb6e1-4f78-4d65-810a-c217ac7f0ddd",
        "76e00719-e688-4f3b-b737-1a306484edf8",
        "F004",
        "00017322",
        "2013-05-08",
        "2183.00",
    ),
    _c(
        "IO",
        22,
        "7fe1ffc9-402b-446c-a12b-360a23b9e5c7",
        "de52d515-2108-49bf-b117-c338ca8f8bd8",
        "F004",
        "00017345",
        "2013-05-13",
        "2183.00",
    ),
    _c(
        "IO",
        23,
        "74918b02-31b8-43ee-b7b6-19cf6c966a0f",
        "3919b029-60cf-4c77-8758-8e284c53c98f",
        "F004",
        "00017382",
        "2013-05-20",
        "1345.20",
    ),
    _c(
        "IO",
        24,
        "9eade5d7-42b5-4dff-8240-b546eb8281ca",
        "dc8f7aa4-985e-4e6b-a45d-dd42b3edc6f4",
        "F002",
        "00410030",
        "2013-05-18",
        "1793.60",
    ),
    _c(
        "IO",
        26,
        "f6650426-d87e-4219-a1da-cb8596760fb6",
        "d2075de9-257f-46c5-b5d3-ddc84cb762cf",
        "F004",
        "00017397",
        "2013-05-21",
        "3492.80",
    ),
    _c(
        "IO",
        28,
        "f5be0d30-9a36-42af-9ec6-2399237a0b9a",
        "f8e6201a-854c-4fd1-ac99-f65671bdb6d0",
        "F002",
        "00145502",
        "2013-06-04",
        "672.60",
    ),
    _c(
        "IO",
        29,
        "ae9456f3-49eb-450f-83a0-6aa004a9bfe8",
        "da4bfb8c-3d2e-4738-bce3-ac72f603cecd",
        "F002",
        "00411236",
        "2013-06-04",
        "654.90",
    ),
    _c(
        "IO",
        34,
        "f8347d53-2cb5-4f26-9bd3-863e972b53ba",
        "053800e6-f3a2-4fc1-9ca8-8c0e78d24cfb",
        "F003",
        "00409960",
        "2013-07-01",
        "1309.80",
    ),
    _c(
        "IO",
        37,
        "9aea4249-12b8-49ac-83b4-81e0486ba543",
        "bb5e9a52-7ad0-4991-9d5d-4ca18e6cfeb7",
        "F023",
        "00048186",
        "2013-07-10",
        "654.90",
    ),
    _c(
        "IO",
        38,
        "a190acf7-a374-4a22-a16f-5074f61fa5c3",
        "3e500fcc-27bf-4a1c-a266-04e83ad5b0eb",
        "F003",
        "00410870",
        "2013-07-16",
        "2690.40",
    ),
    _c(
        "IO",
        49,
        "59872962-0b38-4b58-b399-0c9fb6cf794c",
        "5804a436-2f93-40d3-a1f6-976cdc383250",
        "F004",
        "00018155",
        "2013-08-05",
        "3929.40",
    ),
    _c(
        "IO",
        50,
        "dff3764b-fd4f-481b-9c5f-6c2b38a25197",
        "2bc8f43d-9ad8-4f55-af77-1d5d75e6e218",
        "F004",
        "00018159",
        "2013-08-05",
        "2619.60",
    ),
    _c(
        "IO",
        56,
        "5737ef11-58c8-48f2-b4f9-6c281581f822",
        "f48c359c-a296-4d50-bfd7-f6542e464d7d",
        "F002",
        "00415762",
        "2013-08-19",
        "654.90",
    ),
    _c(
        "IO",
        59,
        "44b5f54e-0cdb-4888-8200-664a76f300f9",
        "88edecf7-2da4-44d7-8380-f9ecbdcd6cbe",
        "F003",
        "00413038",
        "2013-08-21",
        "3138.80",
    ),
    _c(
        "IO",
        60,
        "61aaf739-c716-465d-a044-3cba9167e084",
        "1627a230-53ab-4a1a-85fd-f9e2ba4705f6",
        "F004",
        "00018346",
        "2013-08-22",
        "3492.80",
    ),
    _c(
        "IO",
        61,
        "deb3a149-d135-49bd-b361-da16ad611174",
        "b3d04baa-c3e9-4d6f-874d-cb037000c447",
        "F004",
        "00018350",
        "2013-08-22",
        "1309.80",
    ),
    _c(
        "IO",
        64,
        "55dc858b-8d46-4762-9ca3-b7904913b92c",
        "689475f5-404b-46d4-aa8d-a04f43622e92",
        "F004",
        "00018422",
        "2013-08-29",
        "2152.32",
    ),
    _c(
        "IO",
        65,
        "e6229305-d7e4-4070-afca-3c3318c9e7ee",
        "bae4afe1-b356-4761-9ed8-a93e43ea56fe",
        "F004",
        "00018423",
        "2013-08-29",
        "2152.32",
    ),
    _c(
        "IO",
        68,
        "66059e9b-ab9c-4a97-90db-77c9cfde4ede",
        "1be76995-1b43-4c3d-b006-d720bfa50a82",
        "F003",
        "00413614",
        "2013-09-03",
        "1076.16",
    ),
    _c(
        "IO",
        69,
        "5ee7a203-75df-4d59-af99-73473fed520a",
        "35985d5d-0237-441e-b26d-bb4997688a2b",
        "F004",
        "00018444",
        "2013-09-03",
        "1746.40",
    ),
    _c(
        "IO",
        70,
        "2f5b2abd-8304-43db-84cf-feff7e21b3cf",
        "60ee0cdb-b893-4c58-82a8-7727754298dd",
        "F002",
        "00416910",
        "2013-09-04",
        "2690.40",
    ),
    _c(
        "IO",
        71,
        "cea9966f-a6e4-4b92-aea8-afb19cf554f7",
        "0e911b02-f9c3-4eb0-a6bd-99a8a828c975",
        "F002",
        "00417316",
        "2013-09-09",
        "1793.60",
    ),
    _c(
        "IO",
        73,
        "60b1b5c4-ecdb-49e2-9980-83f262ddf46a",
        "a675c52e-e795-4912-9b32-c725f5473f69",
        "F003",
        "00414583",
        "2013-09-17",
        "1793.60",
    ),
    _c(
        "IO",
        80,
        "935e2161-275d-4073-b089-ba5358758c45",
        "2368b76e-dbd6-4f15-aa2f-198362bada79",
        "F002",
        "00419157",
        "2013-10-01",
        "1309.80",
    ),
    _c(
        "IO",
        83,
        "6840f11b-7654-4ce1-a8a9-3193c48ff076",
        "682d4cf3-09e0-451d-9826-a53829921cea",
        "F004",
        "00018695",
        "2013-10-09",
        "3138.80",
    ),
    _c(
        "IO",
        84,
        "2549cca9-37fa-404d-9385-c51ee865e95d",
        "52b61d5e-cd32-403e-973f-bbb9d9372f3e",
        "F002",
        "00419697",
        "2013-10-09",
        "1345.20",
    ),
    _c(
        "IO",
        86,
        "eb93bd0e-a44e-46d6-a4db-1987993ddf2e",
        "c535b6c0-d094-4fa9-8d11-78618b57533b",
        "F023",
        "00050612",
        "2013-10-11",
        "896.80",
    ),
    _c(
        "IO",
        87,
        "b36b7cc4-0c90-43ec-9831-2586d59fbc40",
        "80e3fa2c-6743-421d-98f6-a2f5a69cf8f8",
        "F023",
        "00050816",
        "2013-10-17",
        "672.60",
    ),
    _c(
        "EDIF",
        16,
        "51a431a1-93d7-4f6a-9f7a-89b009324368",
        "ed9df95d-f7e2-4311-b252-4a991f75d569",
        "002",
        "00005314",
        None,
        "795.90",
    ),
)


MODEL_BY_TYPE = {
    "IO": LiquidacionInspeccionObra,
    "EDIF": LiquidacionEdificacion,
}

LEGACY_MAX_DATE = date(2013, 12, 31)


def has_legacy_identity(comprobante: LiquidacionComprobante, item: Collision) -> bool:
    """Match only the imported invoice identity; amount changes do not hide it."""
    exact_identity = (
        comprobante.serie == item.legacy_serie
        and comprobante.numero == item.legacy_numero
        and comprobante.fecha_emision == item.legacy_fecha
    )
    legacy_date = (
        comprobante.fecha_emision is not None
        and comprobante.fecha_emision <= LEGACY_MAX_DATE
    )
    return exact_identity or legacy_date


class Command(BaseCommand):
    help = (
        "Reconcile the 31 non-legacy comprobantes contaminated by legacy number "
        "collisions. Dry-run by default."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--csv-output", required=True)

    def handle(self, *args, **options):
        rows = []
        operations = []

        for item in COLLISIONS:
            specific = (
                MODEL_BY_TYPE[item.tipo]
                .objects.select_related("liquidacion")
                .filter(
                    numero=item.numero,
                    liquidacion_id=item.liquidacion_id,
                    liquidacion__legacy=False,
                )
                .first()
            )
            base = {
                "tipo": item.tipo,
                "numero": item.numero,
                "liquidacion_id": item.liquidacion_id,
                "comprobante_contaminado_id": item.comprobante_id,
                "legacy_serie": item.legacy_serie,
                "legacy_numero": item.legacy_numero,
                "legacy_fecha": item.legacy_fecha or "",
                "legacy_monto": item.legacy_monto,
                "liquidacion_total": "",
                "comprobante_activo_id": "",
                "actual_serie": "",
                "actual_numero": "",
                "actual_fecha": "",
                "actual_monto": "",
                "status": "",
            }
            if specific is None:
                rows.append({**base, "status": "SKIPPED_LIQUIDACION_MISMATCH"})
                continue

            liquidacion = specific.liquidacion
            base["liquidacion_total"] = liquidacion.total or ""
            contaminated = LiquidacionComprobante.objects.filter(
                id=item.comprobante_id,
                liquidacion_general=liquidacion,
            ).first()
            active = LiquidacionComprobante.objects.filter(
                liquidacion_general=liquidacion,
                activo=True,
            ).first()

            current = active or contaminated
            if current is not None:
                base.update(
                    {
                        "comprobante_activo_id": str(active.id) if active else "",
                        "actual_serie": current.serie or "",
                        "actual_numero": current.numero or "",
                        "actual_fecha": current.fecha_emision or "",
                        "actual_monto": current.monto
                        if current.monto is not None
                        else "",
                    }
                )

            if contaminated is not None and has_legacy_identity(contaminated, item):
                rows.append({**base, "status": "DELETE_CONTAMINATED"})
                operations.append(("delete", contaminated, None))
                continue

            if active is None:
                status = "ALREADY_CLEAN" if contaminated is None else "REVIEW_NO_ACTIVE"
                rows.append({**base, "status": status})
                continue

            if liquidacion.total is None:
                rows.append({**base, "status": "REVIEW_MISSING_LIQUIDACION_TOTAL"})
                continue

            if active.monto != liquidacion.total:
                rows.append({**base, "status": "ADJUST_CORRECTED_AMOUNT"})
                operations.append(("amount", active, liquidacion.total))
            else:
                rows.append({**base, "status": "PRESERVE_CORRECTED"})

        if options["apply"]:
            with transaction.atomic():
                for operation, comprobante, value in operations:
                    if operation == "delete":
                        comprobante.delete()
                    else:
                        comprobante.monto = value
                        comprobante.save(update_fields=["monto", "updated_at"])

        output = Path(options["csv_output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        counts = Counter(row["status"] for row in rows)
        mode = "APPLY" if options["apply"] else "DRY-RUN"
        self.stdout.write(
            self.style.SUCCESS(
                f"=== Non-legacy comprobante reconciliation ({mode}) ==="
            )
        )
        for status, count in sorted(counts.items()):
            self.stdout.write(f"{status}: {count}")
        self.stdout.write(f"CSV: {output}")
