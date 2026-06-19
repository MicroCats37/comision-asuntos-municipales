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
    load_ubigeo → load_delegados_reales (--skip-endpoint by default)

Options:
    --dry-run        Validate seed data and parsing without writing to database
    --with-endpoint  Call load_delegados_reales WITHOUT --skip-endpoint (uses CIP endpoint)
                     Default behavior uses --skip-endpoint (local seeds only)
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
            help='Fetch Colegio details from endpoint (default: use local seeds only)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        with_endpoint = options['with_endpoint']

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

        # ── 2. load_delegados_reales ─────────────────────────────────
        load_delegados_opts = []
        if dry_run:
            load_delegados_opts.append('--dry-run')
        if not with_endpoint:
            load_delegados_opts.append('--skip-endpoint')

        self.stdout.write(f"\n[load_delegados_reales] Loading real delegates...")
        if load_delegados_opts:
            self.stdout.write(f"  Options: {' '.join(load_delegados_opts)}")
        if dry_run and not with_endpoint:
            self.stdout.write("  (using local seeds only, no endpoint)")
        elif dry_run and with_endpoint:
            self.stdout.write("  (dry-run with endpoint fallback)")
        elif with_endpoint:
            self.stdout.write("  (using endpoint as fallback)")

        try:
            call_command('load_delegados_reales', *load_delegados_opts)
            self.stdout.write(self.style.SUCCESS("  [OK] load_delegados_reales completed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [FAIL] load_delegados_reales failed: {e}"))
            raise

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("REAL SEED completed successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))