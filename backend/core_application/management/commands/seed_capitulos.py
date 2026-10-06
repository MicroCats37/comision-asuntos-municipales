"""
Management command to seed Capitulo records from catalogos/capitulos.json.

Idempotent: update_or_create by registro_id.

Uso:
    python manage.py seed_capitulos --settings=config.settings.development
    python manage.py seed_capitulos --dry-run --settings=config.settings.development
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.usuarios.domain.models.perfil_ingeniero import Capitulo


class Command(BaseCommand):
    help = "Seed Capitulo records from catalogos/capitulos.json"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds" / "catalogos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        seed_file = self.SEEDS_DIR / "capitulos.json"
        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        capitulos = data.get("capitulos", [])
        creados = 0
        actualizados = 0

        for item in capitulos:
            registro_id = item["registro_id"]
            abreviacion = item["abreviacion"]
            nombre = item["nombre"]
            grupo_envio_intitucional = item.get("grupo_envio_intitucional")

            defaults = {
                "abreviacion": abreviacion,
                "nombre": nombre,
                "grupo_envio_intitucional": grupo_envio_intitucional,
            }

            if dry_run:
                existing = Capitulo.objects.filter(registro_id=registro_id).first()
                if existing:
                    self.stdout.write(
                        f"  [DRY-RUN] {registro_id} -> ya existe: {nombre} ({abreviacion})"
                    )
                else:
                    self.stdout.write(
                        f"  [DRY-RUN] {registro_id} -> CREAR: {nombre} ({abreviacion})"
                    )
                continue

            _, created = Capitulo.objects.update_or_create(
                registro_id=registro_id,
                defaults=defaults,
            )
            if created:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  [CREADO] {registro_id}: {nombre} ({abreviacion})")
                )
            else:
                actualizados += 1
                self.stdout.write(f"  [ACTUALIZADO] {registro_id}: {nombre} ({abreviacion})")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY-RUN: {len(capitulos)} capitulos validados.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Capitulos: {creados} creados, {actualizados} actualizados."
                )
            )
