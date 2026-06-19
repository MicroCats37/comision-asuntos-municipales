"""
Comando para sembrar datos fiscales: UIT histórico + IGV.
"""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.finanzas.models import UIT, IGV


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
                    self.stdout.write(f"  [DRY-RUN] UIT {item['valor']} ({periodo_inicio}) → ya existe")
                    uit_updated += 1
                else:
                    self.stdout.write(f"  [DRY-RUN] UIT {item['valor']} ({periodo_inicio}) → CREAR")
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
                    self.stdout.write(f"  [DRY-RUN] IGV {item['valor']} ({periodo_inicio}) → ya existe")
                    igv_updated += 1
                else:
                    self.stdout.write(f"  [DRY-RUN] IGV {item['valor']} ({periodo_inicio}) → CREAR")
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

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: No se escribió en la base de datos."))