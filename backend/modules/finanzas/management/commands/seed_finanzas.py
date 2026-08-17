"""
Comando para sembrar datos fiscales: UIT histórico + IGV + Escala de Descuento.
"""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.finanzas.models import UIT, IGV
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)


class Command(BaseCommand):
    help = "Siembra datos fiscales: UIT histórico (2000-2026) e IGV actual (18%)."

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # --- UIT ---
        uit_file = self.SEEDS_DIR / "uit_historico.json"
        if not uit_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {uit_file}"))
            return

        with open(uit_file, encoding="utf-8") as f:
            uit_data = json.load(f)

        uit_created = 0
        uit_updated = 0

        for item in uit_data["uit_values"]:
            periodo_inicio = date.fromisoformat(item["periodo_inicio"])
            periodo_fin = None if item["periodo_fin"] is None else date.fromisoformat(item["periodo_fin"])

            if dry_run:
                existing = UIT.objects.filter(periodo_inicio=periodo_inicio).first()
                if existing:
                    self.stdout.write(f"  [DRY-RUN] UIT {item['valor']} ({periodo_inicio}) -> ya existe")
                    uit_updated += 1
                else:
                    self.stdout.write(f"  [DRY-RUN] UIT {item['valor']} ({periodo_inicio}) -> CREAR")
                    uit_created += 1
                continue

            obj, created = UIT.objects.update_or_create(
                periodo_inicio=periodo_inicio,
                defaults={
                    "valor": Decimal(str(item["valor"])),
                    "periodo_fin": periodo_fin,
                },
            )
            if created:
                uit_created += 1
            else:
                uit_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"UIT: {uit_created} creados, {uit_updated} actualizados"
            )
        )

        # --- IGV ---
        igv_file = self.SEEDS_DIR / "igv_default.json"
        if not igv_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {igv_file}"))
            return

        with open(igv_file, encoding="utf-8") as f:
            igv_data = json.load(f)

        igv_created = 0
        igv_updated = 0

        for item in igv_data["igv_values"]:
            periodo_inicio = date.fromisoformat(item["periodo_inicio"])
            periodo_fin = None if item["periodo_fin"] is None else date.fromisoformat(item["periodo_fin"])

            if dry_run:
                existing = IGV.objects.filter(periodo_inicio=periodo_inicio).first()
                if existing:
                    self.stdout.write(f"  [DRY-RUN] IGV {item['valor']} ({periodo_inicio}) -> ya existe")
                    igv_updated += 1
                else:
                    self.stdout.write(f"  [DRY-RUN] IGV {item['valor']} ({periodo_inicio}) -> CREAR")
                    igv_created += 1
                continue

            obj, created = IGV.objects.update_or_create(
                periodo_inicio=periodo_inicio,
                defaults={
                    "valor": Decimal(str(item["valor"])),
                    "periodo_fin": periodo_fin,
                },
            )
            if created:
                igv_created += 1
            else:
                igv_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"IGV: {igv_created} creados, {igv_updated} actualizados"
            )
        )

        self._seed_escala_descuento_inspector(dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: No se escribió en la base de datos."))

    def _seed_escala_descuento_inspector(self, dry_run: bool):
        """
        Siembra la escala inicial vigente de descuento para inspectores con sus rangos.

        Idempotente: update_or_create sobre (nombre) para la escala y
        (escala, monto_minimo) para los rangos.

        Rangos:
            0-8000       → 15%
            8000-15000   → 20%
            15000-30000  → 30%
            >=30000      → 40%  (monto_maximo None = sin tope)
        """
        escala_nombre = "Escala 2026"
        periodo_inicio = date(2026, 1, 1)

        if dry_run:
            existing = EscalaDescuentoInspector.objects.filter(
                nombre=escala_nombre
            ).first()
            if existing:
                self.stdout.write(
                    f"  [DRY-RUN] EscalaDescuentoInspector '{escala_nombre}' -> ya existe"
                )
            else:
                self.stdout.write(
                    f"  [DRY-RUN] EscalaDescuentoInspector '{escala_nombre}' -> CREAR"
                )
            return

        escala, created = EscalaDescuentoInspector.objects.update_or_create(
            nombre=escala_nombre,
            defaults={
                "periodo_inicio": periodo_inicio,
                "periodo_fin": None,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"EscalaDescuentoInspector '{escala_nombre}' creada"
                )
            )
        else:
            self.stdout.write(
                f"EscalaDescuentoInspector '{escala_nombre}' ya existía — actualizada"
            )

        rangos_data = [
            {"monto_minimo": "0", "monto_maximo": "8000", "porcentaje_descuento": "0.15"},
            {"monto_minimo": "8000", "monto_maximo": "15000", "porcentaje_descuento": "0.20"},
            {"monto_minimo": "15000", "monto_maximo": "30000", "porcentaje_descuento": "0.30"},
            {"monto_minimo": "30000", "monto_maximo": None, "porcentaje_descuento": "0.40"},
        ]

        rangos_creados = 0
        rangos_actualizados = 0
        for rango_data in rangos_data:
            monto_maximo = (
                None
                if rango_data["monto_maximo"] is None
                else Decimal(rango_data["monto_maximo"])
            )
            rango, r_created = RangoDescuentoInspector.objects.update_or_create(
                escala=escala,
                monto_minimo=Decimal(rango_data["monto_minimo"]),
                defaults={
                    "monto_maximo": monto_maximo,
                    "porcentaje_descuento": Decimal(rango_data["porcentaje_descuento"]),
                },
            )
            if r_created:
                rangos_creados += 1
            else:
                rangos_actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Rangos: {rangos_creados} creados, {rangos_actualizados} actualizados"
            )
        )