"""
Management command to clean __pycache__ directories and reset the development DB.

Usage:
    python manage.py reset_dev --settings=config.settings.development --yes
    python manage.py reset_dev --settings=config.settings.development --yes --with-admin
    python manage.py reset_dev --settings=config.settings.development --yes --with-admin --with-mock

Safety:
    Requires --yes flag to proceed. Without it, the command aborts.
    Only works with sqlite3 engine. Other backends are not modified.
"""

import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


# Directories to skip when searching for __pycache__
SKIP_DIRS = {'.venv', '.git', 'node_modules', '__pypackages__', '.pytest_cache',
             'htmlcov', '.coverage', 'venv', 'env', '.env'}


class Command(BaseCommand):
    help = "Remove __pycache__ dirs and reset the SQLite dev DB to empty tables"

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            required=True,
            help='CONFIRM destructive operations (required to proceed)',
        )
        parser.add_argument(
            '--with-admin',
            action='store_true',
            help='Create admin superuser after reset (DNI: 00000000, password: admin)',
        )
        parser.add_argument(
            '--with-mock',
            action='store_true',
            help='Load mock data after reset (implies --with-admin)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("reset_dev — development reset utility"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        # ── 1. Detect DB engine ─────────────────────────────────────
        db_config = settings.DATABASES.get('default', {})
        engine = db_config.get('ENGINE', '')

        if 'sqlite3' not in engine:
            self.stdout.write(
                self.style.ERROR(
                    f"This command only supports sqlite3 (got: {engine}). "
                    "Other backends must be reset manually."
                )
            )
            return

        db_name = db_config.get('NAME')
        if not db_name:
            self.stdout.write(self.style.ERROR("DATABASES['default']['NAME'] is not set."))
            return

        db_path = Path(db_name)
        if not db_path.is_absolute():
            db_path = Path(settings.BASE_DIR) / db_name

        # ── 2. Confirm or abort ──────────────────────────────────────
        if not options['yes']:
            self.stdout.write(
                self.style.WARNING(
                    "ABORTED: --yes flag is required to proceed.\n"
                    "Add --yes to confirm destructive operations."
                )
            )
            return

        # ── 3. Delete __pycache__ recursively ───────────────────────
        self.stdout.write("\n[1/3] Removing __pycache__ directories...")
        pycache_count = 0
        removed_paths = []

        backend_root = Path(settings.BASE_DIR).resolve()

        for root_dir, dirs, files in os.walk(backend_root, topdown=True):
            # Prune skip dirs in-place to avoid descending into them
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            pycache_dir = Path(root_dir) / '__pycache__'
            if pycache_dir.is_dir():
                try:
                    shutil.rmtree(pycache_dir)
                    pycache_count += 1
                    removed_paths.append(pycache_dir.relative_to(backend_root))
                except OSError as e:
                    self.stdout.write(
                        self.style.WARNING(f"  Could not remove {pycache_dir.relative_to(backend_root)}: {e}")
                    )

        if pycache_count:
            self.stdout.write(
                self.style.SUCCESS(f"  Removed {pycache_count} __pycache__ directory(ies)")
            )
            for p in removed_paths[:5]:
                self.stdout.write(f"    - {p}")
            if len(removed_paths) > 5:
                self.stdout.write(f"    ... and {len(removed_paths) - 5} more")
        else:
            self.stdout.write(self.style.WARNING("  No __pycache__ directories found"))

        # ── 4. Delete SQLite DB file ────────────────────────────────
        self.stdout.write(f"\n[2/3] Resetting DB at {db_path}...")
        if db_path.exists():
            try:
                db_path.unlink()
                self.stdout.write(self.style.SUCCESS(f"  Deleted: {db_path}"))
            except OSError as e:
                self.stdout.write(self.style.ERROR(f"  Could not delete DB file: {e}"))
                return
        else:
            self.stdout.write(self.style.WARNING(f"  DB file not found (nothing to delete): {db_path}"))

        # ── 5. Run migrations ───────────────────────────────────────
        self.stdout.write("\n[3/3] Running migrations...")
        call_command('migrate', '--noinput', verbosity=1)
        self.stdout.write(self.style.SUCCESS("  Migrations complete — DB is now empty with schema"))

        # ── 6. Optional: create admin ────────────────────────────────
        if options.get('with_admin') or options.get('with_mock'):
            self.stdout.write("\n[+] Creating admin superuser...")
            call_command('create_admin', verbosity=1)

        # ── 7. Optional: load mock data ─────────────────────────────
        if options.get('with_mock'):
            self.stdout.write("\n[+] Loading mock data...")
            call_command('mock_data', '--skip-admin', verbosity=1)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("reset_dev completed successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))