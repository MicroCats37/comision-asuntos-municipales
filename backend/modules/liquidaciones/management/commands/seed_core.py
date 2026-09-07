"""
Management command to orchestrate ONLY the essential reference-data seeds
in correct dependency order.

Essential reference data (core):
    1. load_ubigeo          (geographic reference — Ubigeo)
    2. seed_municipalidades (municipalities with L* codes)
    3. seed_especialidades  (EspecialidadRevision — REQUIRED before tarifas)
    4. seed_finanzas        (UIT + IGV + EscalaDescuentoInspector + TasaDelegado)
    5. seed_codigos_liquidacion  (LiquidacionCodigo per TipoLiquidacion)
    6. seed_tarifas_all     (all tariff tables — needs EspecialidadRevision first)

NOT included (domain/import data — not core reference data):
    - seed_delegados
    - seed_inspectores
    - seed_colegiados
    - seed_perfiles_ingeniero_faltantes

Usage:
    python manage.py seed_core --settings=config.settings.development
    python manage.py seed_core --dry-run --settings=config.settings.development
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Orchestrate essential reference-data seeds in dependency order."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate seed data without writing to database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("SEED CORE — Essential reference data"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("  [DRY-RUN MODE] — No database writes will occur")
            )
            self.stdout.write("")

        steps = [
            ("load_ubigeo", "Ubigeo geographic reference"),
            ("seed_municipalidades", "Municipalities (L* codes)"),
            ("seed_especialidades", "EspecialidadRevision values"),
            ("seed_finanzas", "UIT / IGV / EscalaDescuentoInspector / TasaDelegado"),
            ("seed_codigos_liquidacion", "LiquidacionCodigo per TipoLiquidacion"),
            ("seed_tarifas_all", "All tariff tables"),
        ]

        for i, (command_name, description) in enumerate(steps, 1):
            self.stdout.write(f"\n[{i}/{len(steps)}] {description}")
            self.stdout.write(f"         Running: {command_name}")

            if dry_run and command_name != "seed_especialidades":
                # seed_especialidades is safe to run even in dry-run since it's a pure seed
                self.stdout.write(f"         SKIPPED (dry-run mode — mutates DB)")
                continue

            try:
                call_command(command_name, **{"dry_run": True} if dry_run else {})
                self.stdout.write(
                    self.style.SUCCESS(f"         [OK] {command_name} completed")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"         [FAIL] {command_name} failed: {e}")
                )
                raise

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("SEED CORE completed successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
