"""
Comando para sembrar municipalidades desde seeds/municipalidades.json.

Idempotente: usa update_or_create por codigo.
provincia/distrito quedan null (se asignan en una fase posterior si aplica).

Uso:
    python manage.py seed_municipalidades --settings=config.settings.development
    python manage.py seed_municipalidades --dry-run --settings=config.settings.development
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.entidades.domain.models.municipalidad import Municipalidad


class Command(BaseCommand):
    help = "Siembra municipalidades desde seeds/municipalidades.json"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        seed_file = self.SEEDS_DIR / "municipalidades.json"
        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        municipios = data.get("municipalidades", [])
        created = 0
        updated = 0

        for item in municipios:
            codigo = item["codigo"]
            nombre = item["nombre"]

            if dry_run:
                self.stdout.write(f"[DRY] {codigo} -> {nombre}")
                continue

            _, was_created = Municipalidad.objects.update_or_create(
                codigo=codigo,
                defaults={"nombre": nombre},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: {len(municipios)} municipalidades validadas."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Municipalidades: {created} creadas, {updated} actualizadas."
                )
            )
