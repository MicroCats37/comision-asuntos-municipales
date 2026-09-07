"""
Management command to seed the canonical EspecialidadRevision values.

These are required by seed_tarifas_all before it can populate tariff data.

Canonical values:
    - Ingeniería Civil
    - Ingeniería Electrónica
    - Ingeniería Eléctrica y Mecánica Eléctrica
    - Ingeniería Sanitaria

Idempotent: get_or_create by nombre.

Usage:
    python manage.py seed_especialidades --settings=config.settings.development
    python manage.py seed_especialidades --dry-run --settings=config.settings.development
"""

from django.core.management.base import BaseCommand

from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


# Canonical EspecialidadRevision values.
# slug is derived from the nombre (kebab-case).
CANONICAL_ESPECIALIDADES = [
    {
        "nombre": "Ingeniería Civil",
        "slug": "ingenieria-civil",
    },
    {
        "nombre": "Ingeniería Electrónica",
        "slug": "ingenieria-electronica",
    },
    {
        "nombre": "Ingeniería Eléctrica y Mecánica Eléctrica",
        "slug": "ingenieria-electrica-y-mecanica-electrica",
    },
    {
        "nombre": "Ingeniería Sanitaria",
        "slug": "ingenieria-sanitaria",
    },
]


class Command(BaseCommand):
    help = "Seed canonical EspecialidadRevision values."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate without writing to database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("[DRY-RUN] EspecialidadRevision values that would be seeded:")
            )
            for esp in CANONICAL_ESPECIALIDADES:
                exists = EspecialidadRevision.objects.filter(nombre=esp["nombre"]).exists()
                status = "EXISTS" if exists else "CREATE"
                self.stdout.write(f"  [{status}] {esp['nombre']} (slug={esp['slug']})")
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING("DRY-RUN: No database writes will occur.")
            )
            return

        creados = 0
        ya_existen = 0

        for esp in CANONICAL_ESPECIALIDADES:
            obj, created = EspecialidadRevision.objects.get_or_create(
                nombre=esp["nombre"],
                defaults={"slug": esp["slug"]},
            )
            if created:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Created: {obj.nombre}")
                )
            else:
                ya_existen += 1
                self.stdout.write(f"  Exists: {obj.nombre}")

        self.stdout.write(
            self.style.SUCCESS(
                f"EspecialidadRevision: {creados} created, {ya_existen} already existed."
            )
        )
