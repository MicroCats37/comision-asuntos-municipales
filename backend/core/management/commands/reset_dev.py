"""
Development reset command for local artifacts and database state.

Usage:
    python manage.py reset_dev --settings=config.settings.development
    python manage.py reset_dev --settings=config.settings.development --yes
    python manage.py reset_dev --settings=config.settings.development --yes --migrations --cache
"""

import os
import shutil
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


SKIP_DIRS = {
    ".coverage",
    ".env",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pypackages__",
    "env",
    "htmlcov",
    "node_modules",
    "venv",
}


class Command(BaseCommand):
    help = "Clean local migrations, Python cache artifacts, and development database state."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="CONFIRM destructive operations. Without this flag the command runs in dry-run mode.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Clean migrations, cache artifacts, and database state (default).",
        )
        parser.add_argument(
            "--migrations",
            action="store_true",
            help="Delete local app migration files, preserving migrations/__init__.py.",
        )
        parser.add_argument(
            "--cache",
            action="store_true",
            help="Delete __pycache__ directories and .pyc/.pyo files under the backend project.",
        )
        parser.add_argument(
            "--database",
            action="store_true",
            help="Reset the configured development database state.",
        )
        parser.add_argument(
            "--skip-migrate",
            action="store_true",
            help="Do not run migrate --run-syncdb after deleting a SQLite database file.",
        )
        parser.add_argument(
            "--with-admin",
            action="store_true",
            help="Create the development admin user after database reset.",
        )
        parser.add_argument(
            "--with-real-seed",
            action="store_true",
            help="Load real canonical seed data after database reset.",
        )

    def handle(self, *args, **options):
        backend_root = Path(settings.BASE_DIR).resolve()
        selected = self._selected_actions(options)
        dry_run = not options["yes"]

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("reset_dev - development reset utility"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Backend root: {backend_root}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN MODE: no files or database records will be deleted. "
                    "Add --yes to execute."
                )
            )

        if not self._is_development_settings():
            raise CommandError(
                "Refusing to reset artifacts outside a development/debug settings module. "
                "Run with --settings=config.settings.development."
            )

        if selected["migrations"]:
            self._clean_migrations(backend_root, dry_run)

        if selected["cache"]:
            self._clean_cache(backend_root, dry_run)

        if selected["database"]:
            self._reset_database(backend_root, dry_run, options, selected)
        elif options["with_admin"] or options["with_real_seed"]:
            raise CommandError("--with-admin and --with-real-seed require --database or --all.")

        self.stdout.write(self.style.SUCCESS("\nreset_dev completed." if not dry_run else "\nreset_dev dry-run completed."))

    def _selected_actions(self, options):
        explicit = options["migrations"] or options["cache"] or options["database"]
        run_all = options["all"] or not explicit
        return {
            "migrations": run_all or options["migrations"],
            "cache": run_all or options["cache"],
            "database": run_all or options["database"],
        }

    def _is_development_settings(self):
        settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
        return bool(settings.DEBUG) or settings_module.endswith(".development")

    def _local_app_paths(self, backend_root):
        paths = []
        for app_config in apps.get_app_configs():
            app_path = Path(app_config.path).resolve()
            if not self._is_relative_to(app_path, backend_root):
                continue
            if app_config.name == "core" or app_config.name.startswith("modules."):
                paths.append(app_path)
        return sorted(paths)

    def _clean_migrations(self, backend_root, dry_run):
        self.stdout.write("\n[1/3] Cleaning local app migrations...")
        targets = []

        for app_path in self._local_app_paths(backend_root):
            migrations_dir = app_path / "migrations"
            if not migrations_dir.is_dir():
                continue
            for path in migrations_dir.iterdir():
                if path.name == "__init__.py" or path.name == "__pycache__":
                    continue
                if path.is_file() and path.suffix == ".py":
                    targets.append(path)

        self._report_paths("migration file", targets, backend_root)
        if dry_run:
            return

        for path in targets:
            path.unlink()

    def _clean_cache(self, backend_root, dry_run):
        self.stdout.write("\n[2/3] Cleaning Python cache artifacts...")
        pycache_dirs = []
        bytecode_files = []

        for root, dirs, files in os.walk(backend_root, topdown=True):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
            root_path = Path(root)

            for dirname in dirs:
                if dirname == "__pycache__":
                    pycache_dirs.append(root_path / dirname)

            for filename in files:
                path = root_path / filename
                if path.suffix in {".pyc", ".pyo"}:
                    bytecode_files.append(path)

        targets = sorted(pycache_dirs) + sorted(bytecode_files)
        self._report_paths("cache artifact", targets, backend_root)
        if dry_run:
            return

        for path in sorted(bytecode_files):
            if path.exists():
                path.unlink()
        for path in sorted(pycache_dirs, key=lambda item: len(item.parts), reverse=True):
            if path.exists():
                shutil.rmtree(path)

    def _reset_database(self, backend_root, dry_run, options, selected):
        self.stdout.write("\n[3/3] Resetting development database...")
        db_config = settings.DATABASES.get("default", {})
        engine = db_config.get("ENGINE", "")

        if "sqlite3" in engine:
            db_path = self._sqlite_db_path(db_config, backend_root)
            self.stdout.write(f"  SQLite database: {db_path}")
            if dry_run:
                self.stdout.write("  Would delete SQLite database file if it exists.")
                if not options["skip_migrate"]:
                    if selected["migrations"]:
                        self.stdout.write("  Would sync local apps without migration files.")
                    self.stdout.write("  Would run migrate --run-syncdb --noinput afterwards.")
                return

            if db_path.exists():
                from django.db import connection
                connection.close()
                db_path.unlink()
                self.stdout.write(self.style.SUCCESS(f"  Deleted: {db_path}"))
            else:
                self.stdout.write(self.style.WARNING(f"  Database file not found: {db_path}"))

            if not options["skip_migrate"]:
                if selected["migrations"]:
                    self._disable_local_migrations_for_syncdb(backend_root)
                call_command("migrate", "--run-syncdb", "--noinput", verbosity=1)
                self.stdout.write(self.style.SUCCESS("  Database schema recreated."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"  Non-SQLite database detected ({engine}). Will use Django flush instead of dropping the database."
                )
            )
            if dry_run:
                self.stdout.write("  Would run flush --noinput.")
                return
            call_command("flush", "--noinput", verbosity=1)
            self.stdout.write(self.style.SUCCESS("  Database flushed."))

        if options["with_admin"] or options["with_real_seed"]:
            call_command("create_admin", verbosity=1)

        if options["with_real_seed"]:
            call_command("seed_real_all", verbosity=1)

    def _disable_local_migrations_for_syncdb(self, backend_root):
        migration_modules = dict(getattr(settings, "MIGRATION_MODULES", {}) or {})
        for app_config in apps.get_app_configs():
            app_path = Path(app_config.path).resolve()
            if not self._is_relative_to(app_path, backend_root):
                continue
            if app_config.name == "core" or app_config.name.startswith("modules."):
                migration_modules[app_config.label] = None
        settings.MIGRATION_MODULES = migration_modules

    def _sqlite_db_path(self, db_config, backend_root):
        db_name = db_config.get("NAME")
        if not db_name or db_name == ":memory:":
            raise CommandError("SQLite DATABASES['default']['NAME'] must be a local file path.")

        db_path = Path(db_name)
        if not db_path.is_absolute():
            db_path = backend_root / db_path
        db_path = db_path.resolve()

        if not self._is_relative_to(db_path, backend_root):
            raise CommandError(f"Refusing to delete SQLite DB outside backend root: {db_path}")
        return db_path

    def _report_paths(self, label, paths, backend_root):
        if not paths:
            self.stdout.write(self.style.WARNING(f"  No {label}s found."))
            return

        self.stdout.write(f"  Found {len(paths)} {label}(s).")
        for path in paths[:10]:
            self.stdout.write(f"    - {path.relative_to(backend_root)}")
        if len(paths) > 10:
            self.stdout.write(f"    ... and {len(paths) - 10} more")

    def _is_relative_to(self, path, parent):
        try:
            path.relative_to(parent)
        except ValueError:
            return False
        return True
