"""Corrige snapshots de propietario y razón social de EDIF legacy desde EDIF_ALL.csv."""
from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)


DEFAULT_CSV_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "core_application"
    / "seeds"
    / "historico"
    / "EDIF_ALL.csv"
)


def clean(value: str | None) -> str | None:
    value = value.strip() if value else ""
    return value or None


class Command(BaseCommand):
    help = (
        "Corrige nombre_propietario=NOMBRE y entidad_razon_social=RAZONSOCIAL "
        "para Edificaciones legacy. Dry-run por defecto; use --apply para persistir."
    )

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH))
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.is_file():
            raise CommandError(f"No existe el CSV: {csv_path}")

        csv_rows = self._load_rows(csv_path)
        operations = list(
            LiquidacionEdificacion.objects.select_related("liquidacion__proyecto")
            .filter(
                liquidacion__legacy=True,
                numero__in=csv_rows,
            )
            .order_by("numero")
        )

        matched_numbers = {operation.numero for operation in operations}
        changes = []
        for operation in operations:
            owner, razon_social = csv_rows[operation.numero]
            project = operation.liquidacion.proyecto
            if (
                project.nombre_propietario != owner
                or project.entidad_razon_social != razon_social
            ):
                changes.append((project, owner, razon_social))

        self.stdout.write(f"CSV IDs: {len(csv_rows)}")
        self.stdout.write(f"Edificaciones legacy encontradas: {len(operations)}")
        self.stdout.write(f"IDs CSV sin liquidación legacy: {len(csv_rows) - len(matched_numbers)}")
        self.stdout.write(f"Proyectos a corregir: {len(changes)}")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Dry-run: no se modificó ningún registro."))
            return

        with transaction.atomic():
            for project, owner, razon_social in changes:
                project.nombre_propietario = owner
                project.entidad_razon_social = razon_social
                project.save(update_fields=["nombre_propietario", "entidad_razon_social", "updated_at"])

        self.stdout.write(self.style.SUCCESS(f"Corregidos {len(changes)} proyectos legacy EDIF."))

    @staticmethod
    def _load_rows(csv_path: Path) -> dict[int, tuple[str, str | None]]:
        rows: dict[int, tuple[str, str | None]] = {}
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            for line_number, row in enumerate(csv.DictReader(source, delimiter=";"), start=2):
                raw_id = clean(row.get("ID"))
                owner = clean(row.get("NOMBRE"))
                if raw_id is None or owner is None:
                    continue
                try:
                    row_id = int(float(raw_id))
                except ValueError as exc:
                    raise CommandError(f"ID inválido en línea {line_number}: {raw_id!r}") from exc

                values = (owner, clean(row.get("RAZONSOCIAL")))
                previous = rows.get(row_id)
                if previous is not None and previous != values:
                    raise CommandError(
                        f"ID duplicado con datos distintos en línea {line_number}: {row_id}"
                    )
                rows[row_id] = values
        return rows
