"""
Management command to orchestrate real seed data commands in dependency order.

This command loads OFFICIAL/CANONICAL data only:
  - Ubigeo (geographic reference data)
  - Delegados reales (CAM delegates from official documents)

Usage:
    python manage.py seed_real_all --settings=config.settings.development
    python manage.py seed_real_all --dry-run --settings=config.settings.development
    python manage.py seed_real_all --with-endpoint --settings=config.settings.development

Dependency order:
    load_ubigeo → seed_delegados

Options:
    --dry-run        Validate seed data and parsing without writing to database
    --with-endpoint  (Currently a no-op for seed_delegados; kept for compatibility)
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Orchestrate real seed data commands (ubigeo + delegados reales)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate seed data without writing to database',
        )
        parser.add_argument(
            '--with-endpoint',
            action='store_true',
            help='(No-op; kept for compatibility with existing scripts)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        # with_endpoint is intentionally ignored — seed_delegados uses local seeds only.

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("REAL SEED — Loading official canonical data"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if dry_run:
            self.stdout.write(self.style.WARNING("  [DRY-RUN MODE] — No database writes will occur"))
            self.stdout.write("")

        # ── 1. load_ubigeo ────────────────────────────────────────────
        # Note: load_ubigeo is idempotent (update_or_create), safe to re-run.
        # For dry-run, we skip it since it mutates DB.
        if dry_run:
            self.stdout.write("[load_ubigeo] SKIPPED (dry-run mode — mutates DB)")
        else:
            self.stdout.write("\n[load_ubigeo] Loading Ubigeo geographic data...")
            try:
                call_command('load_ubigeo')
                self.stdout.write(self.style.SUCCESS("  [OK] load_ubigeo completed"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [FAIL] load_ubigeo failed: {e}"))
                raise

        # ── 2. seed_delegados ─────────────────────────────────────────
        self.stdout.write("\n[seed_delegados] Loading real delegates...")
        try:
            call_command('seed_delegados', **({"dry_run": True} if dry_run else {}))
            self.stdout.write(self.style.SUCCESS("  [OK] seed_delegados completed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [FAIL] seed_delegados failed: {e}"))
            raise

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("REAL SEED completed successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))