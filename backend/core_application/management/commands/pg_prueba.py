"""PostgreSQL Prueba migration commands — single entry point with subcommands.

Usage:
    pg_prueba validate-scope      [--sqlite PATH] [--target DSN] [--apps APP..] [--show-all]
    pg_prueba generate-sqlite-sql [--sqlite PATH] [--target DSN] [--output PATH]
                                   [--batch-size N] [--truncate] [--disable-triggers]
                                   [--mode upsert|ignore|insert]
    pg_prueba apply-sql           [--sql PATH] [--target DSN] [--via-docker]
                                   [--execute] [--yes]
    pg_prueba generate-final-sql  [--source DSN] [--output PATH] [--batch-size N]
                                   [--truncate] [--disable-triggers]
                                   [--mode upsert|ignore|insert]
    pg_prueba pipeline            [--sqlite PATH] [--sqlite-sql PATH] [--final-sql PATH]
                                   [--test-target DSN] [--batch-size N]
                                   [--mode upsert|ignore|insert] [--apply-to-test]
                                   [--via-docker] [--truncate-test]
                                   [--disable-triggers-for-test-sql]
                                   [--disable-triggers-for-final-sql] [--truncate]
                                   [--dry-run]
"""

import shutil
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ._pg_prueba.common import (
    BUSINESS_TABLES,
    DEFAULT_APPS,
    DEFAULT_SQLITE_PATH,
    DEFAULT_SQLITE_SQL,
    DEFAULT_TEST_DSN,
    POSTGRES_PRUEBA_DIR,
    default_final_sql,
    django_operational_tables,
    find_safety_markers,
    postgres_tables,
    sqlite_tables,
)
from ._pg_prueba.generators import generate_final_sql, generate_sqlite_sql


DOCKER_SERVICE = "postgres_prueba"
DOCKER_DB = "cam_db_prueba"
DOCKER_USER = "cam_user"


class Command(BaseCommand):
    help = __doc__.split("\n\n")[0]

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", title="actions", description="Available subcommands")

        # ── validate-scope ──────────────────────────────────────────────────────
        p = subparsers.add_parser("validate-scope", help="Validate postgres_prueba table scope against Django models.")
        p.add_argument("--sqlite", default=None, help="Optional SQLite DB path to verify table existence.")
        p.add_argument("--target", default=None, help="Optional PostgreSQL prueba DSN to verify table existence.")
        p.add_argument(
            "--apps",
            nargs="+",
            default=list(DEFAULT_APPS),
            help="Django app labels considered operational migration scope.",
        )
        p.add_argument("--show-all", action="store_true", help="Print every expected/configured table.")

        # ── generate-sqlite-sql ─────────────────────────────────────────────────
        p = subparsers.add_parser(
            "generate-sqlite-sql", help="Generate postgres_prueba SQL from the SQLite source database."
        )
        p.add_argument("--sqlite", default=str(DEFAULT_SQLITE_PATH))
        p.add_argument("--target", default=DEFAULT_TEST_DSN, help="PostgreSQL prueba DSN used for column metadata.")
        p.add_argument("--output", default=str(DEFAULT_SQLITE_SQL))
        p.add_argument("--batch-size", type=int, default=250)
        p.add_argument("--truncate", action="store_true", help="Opt-in only: include TRUNCATE TABLE.")
        p.add_argument(
            "--disable-triggers",
            action="store_true",
            help="Opt-in only: write session_replication_role around the data load.",
        )
        p.add_argument(
            "--mode",
            choices=("upsert", "ignore", "insert"),
            default="upsert",
            help="Conflict behavior for generated SQL.",
        )

        # ── apply-sql ──────────────────────────────────────────────────────────
        p = subparsers.add_parser("apply-sql", help="Apply a generated SQL file to PostgreSQL prueba; dry-run by default.")
        p.add_argument("--sql", default=str(DEFAULT_SQLITE_SQL), help="SQL file to apply.")
        p.add_argument("--target", default=DEFAULT_TEST_DSN, help="PostgreSQL prueba DSN.")
        p.add_argument("--via-docker", action="store_true", help="Run psql inside docker compose service.")
        p.add_argument("--execute", action="store_true", help="Actually apply the SQL.")
        p.add_argument("--yes", action="store_true", help="Required with --execute to confirm mutation.")

        # ── generate-final-sql ──────────────────────────────────────────────────
        p = subparsers.add_parser(
            "generate-final-sql", help="Generate final server SQL from the validated PostgreSQL prueba database."
        )
        p.add_argument("--source", default=DEFAULT_TEST_DSN, help="PostgreSQL prueba source DSN.")
        p.add_argument("--output", default=None)
        p.add_argument("--batch-size", type=int, default=1000)
        p.add_argument("--truncate", action="store_true", help="Opt-in only: include TRUNCATE TABLE.")
        p.add_argument(
            "--disable-triggers",
            action="store_true",
            help="Opt-in only: write session_replication_role around the data load.",
        )
        p.add_argument(
            "--mode",
            choices=("upsert", "ignore", "insert"),
            default="upsert",
            help="Conflict behavior for generated SQL.",
        )

        # ── pipeline ──────────────────────────────────────────────────────────
        p = subparsers.add_parser("pipeline", help="Run the safe SQLite -> PostgreSQL prueba -> final SQL pipeline.")
        p.add_argument("--sqlite", default=str(DEFAULT_SQLITE_PATH))
        p.add_argument("--sqlite-sql", default=str(DEFAULT_SQLITE_SQL))
        p.add_argument("--final-sql", default=None)
        p.add_argument("--test-target", default=DEFAULT_TEST_DSN)
        p.add_argument("--batch-size", type=int, default=1000)
        p.add_argument(
            "--mode",
            choices=("upsert", "ignore", "insert"),
            default="upsert",
            help="Conflict behavior used by generated SQL files.",
        )
        p.add_argument("--apply-to-test", action="store_true", help="Mutate PostgreSQL prueba after generation.")
        p.add_argument("--via-docker", action="store_true", help="When applying, run psql through docker compose.")
        p.add_argument(
            "--truncate-test",
            action="store_true",
            help="Include TRUNCATE only in the SQLite-generated SQL applied to PostgreSQL prueba.",
        )
        p.add_argument(
            "--disable-triggers-for-test-sql",
            action="store_true",
            help="Opt-in only: write session_replication_role into SQLite-generated SQL.",
        )
        p.add_argument(
            "--disable-triggers-for-final-sql",
            action="store_true",
            help="Opt-in only: write session_replication_role into final SQL.",
        )
        p.add_argument("--truncate", action="store_true", help="Opt-in only: include TRUNCATE in generated SQL files.")
        p.add_argument("--dry-run", action="store_true", help="Print steps without generating or applying SQL.")

    def handle(self, *args, **options):
        action = options.pop("action", None)
        if not action:
            raise CommandError("No action specified. Run with --help to see available subcommands.")

        # Dispatch to the appropriate handler
        handler = getattr(self, f"_handle_{action.replace('-', '_')}", None)
        if not handler:
            raise CommandError(f"Unknown action: {action}")
        handler(options)

    # ── validate-scope ─────────────────────────────────────────────────────────

    def _handle_validate_scope(self, options):
        configured = set(BUSINESS_TABLES)
        expected = django_operational_tables(tuple(options["apps"]))

        missing_from_config = expected - configured
        extra_in_config = configured - expected
        failures = [missing_from_config, extra_in_config]

        self.stdout.write("Migration scope validation")
        self.stdout.write(f"apps={', '.join(options['apps'])}")
        self.stdout.write(f"expected_from_django={len(expected)}")
        self.stdout.write(f"configured_business_tables={len(configured)}")

        if options["show_all"]:
            self._print_list("Expected operational Django tables", expected)
            self._print_list("Configured BUSINESS_TABLES", configured)

        self._print_list("Missing from BUSINESS_TABLES", missing_from_config)
        self._print_list("Extra in BUSINESS_TABLES", extra_in_config)

        if options["sqlite"]:
            sqlite_path = Path(options["sqlite"])
            if not sqlite_path.exists():
                raise CommandError(f"SQLite database not found: {sqlite_path}")
            sqlite_existing = sqlite_tables(sqlite_path)
            expected_missing_in_sqlite = expected - sqlite_existing
            configured_missing_in_sqlite = configured - sqlite_existing
            failures.extend([expected_missing_in_sqlite, configured_missing_in_sqlite])
            self.stdout.write(f"sqlite={sqlite_path}")
            self._print_list("Expected Django tables missing in SQLite", expected_missing_in_sqlite)
            self._print_list("Configured BUSINESS_TABLES missing in SQLite", configured_missing_in_sqlite)

        if options["target"]:
            pg_existing = postgres_tables(options["target"])
            expected_missing_in_pg = expected - pg_existing
            configured_missing_in_pg = configured - pg_existing
            failures.extend([expected_missing_in_pg, configured_missing_in_pg])
            self.stdout.write(f"target={options['target']}")
            self._print_list("Expected Django tables missing in PostgreSQL prueba", expected_missing_in_pg)
            self._print_list("Configured BUSINESS_TABLES missing in PostgreSQL prueba", configured_missing_in_pg)

        if any(failures):
            raise CommandError("RESULT=FAIL")
        self.stdout.write(self.style.SUCCESS("RESULT=OK"))

    def _print_list(self, title: str, values: set[str]):
        self.stdout.write(f"\n{title} ({len(values)})")
        if not values:
            self.stdout.write("  - none")
            return
        for value in sorted(values):
            self.stdout.write(f"  - {value}")

    # ── generate-sqlite-sql ────────────────────────────────────────────────────

    def _handle_generate_sqlite_sql(self, options):
        try:
            generate_sqlite_sql(
                sqlite_path=Path(options["sqlite"]),
                target_dsn=options["target"],
                output_path=Path(options["output"]),
                batch_size=options["batch_size"],
                mode=options["mode"],
                truncate=options["truncate"],
                disable_triggers=options["disable_triggers"],
                stdout=self.stdout,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

    # ── apply-sql ─────────────────────────────────────────────────────────────

    def _handle_apply_sql(self, options):
        sql_file = Path(options["sql"]).resolve()
        if not sql_file.exists():
            raise CommandError(f"SQL file not found: {sql_file}")

        if options["via_docker"]:
            command = self._docker_command()
            display = " ".join(command) + f" < {sql_file}"
        else:
            command = ["psql", "-v", "ON_ERROR_STOP=1", "-f", str(sql_file), options["target"]]
            display = " ".join(command)

        self.stdout.write(f"SQL file: {sql_file}")
        target = f"docker compose service {DOCKER_SERVICE}" if options["via_docker"] else options["target"]
        self.stdout.write(f"Target: {target}")
        self.stdout.write(f"Command: {display}")

        markers = find_safety_markers(sql_file)
        if markers:
            self.stdout.write(self.style.WARNING("WARNING: safety-sensitive SQL markers found:"))
            for marker in markers:
                self.stdout.write(f"  {marker}")

        if not options["execute"]:
            self.stdout.write("Dry-run only. Add --execute --yes to apply this SQL to PostgreSQL prueba.")
            return
        if not options["yes"]:
            raise CommandError("--execute requires --yes to confirm this database mutation.")

        if options["via_docker"]:
            if shutil.which("docker") is None:
                raise CommandError("docker was not found in PATH")
            with sql_file.open("rb") as sql_input:
                result = subprocess.run(command, stdin=sql_input, check=False)
        else:
            if shutil.which("psql") is None:
                raise CommandError("psql was not found in PATH. Use --via-docker or install PostgreSQL client tools.")
            result = subprocess.run(command, check=False)

        if result.returncode != 0:
            raise CommandError(f"psql exited with code {result.returncode}")

    def _docker_command(self):
        return [
            "docker",
            "compose",
            "--project-directory",
            str(POSTGRES_PRUEBA_DIR),
            "exec",
            "-T",
            DOCKER_SERVICE,
            "psql",
            "-U",
            DOCKER_USER,
            "-d",
            DOCKER_DB,
            "-v",
            "ON_ERROR_STOP=1",
        ]

    # ── generate-final-sql ─────────────────────────────────────────────────────

    def _handle_generate_final_sql(self, options):
        output = options["output"]
        if output is None:
            output = str(default_final_sql())
        try:
            generate_final_sql(
                source_dsn=options["source"],
                output_path=Path(output),
                batch_size=options["batch_size"],
                mode=options["mode"],
                truncate=options["truncate"],
                disable_triggers=options["disable_triggers"],
                stdout=self.stdout,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

    # ── pipeline ──────────────────────────────────────────────────────────────

    def _handle_pipeline(self, options):
        steps = self._pipeline_steps(options)
        for title, handler_name, kwargs in steps:
            self.stdout.write(f"\n=== {title} ===")
            self.stdout.write(self._format_step(handler_name, kwargs))
            if options["dry_run"]:
                continue
            handler = getattr(self, handler_name, None)
            if handler:
                handler(kwargs)
            else:
                raise CommandError(f"Unknown pipeline step: {handler_name}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY-RUN: no SQL was generated or applied."))

    def _pipeline_steps(self, options):
        sqlite_sql = options["sqlite_sql"]
        final_sql = options["final_sql"]
        if final_sql is None:
            final_sql = str(default_final_sql())
        test_target = options["test_target"]

        steps = [
            (
                "Validate migration scope",
                "_handle_validate_scope",
                {
                    "apps": list(DEFAULT_APPS),
                    "show_all": False,
                    "sqlite": options["sqlite"],
                    "target": test_target,
                },
            ),
            (
                "Generate SQLite SQL",
                "_handle_generate_sqlite_sql",
                {
                    "sqlite": options["sqlite"],
                    "target": test_target,
                    "output": sqlite_sql,
                    "mode": options["mode"],
                    "batch_size": 250,
                    "truncate": options["truncate"] or options["truncate_test"],
                    "disable_triggers": options["disable_triggers_for_test_sql"],
                },
            ),
        ]

        if options["apply_to_test"]:
            steps.append(
                (
                    "Apply SQL to PostgreSQL prueba",
                    "_handle_apply_sql",
                    {
                        "sql": sqlite_sql,
                        "target": test_target,
                        "via_docker": options["via_docker"],
                        "execute": True,
                        "yes": True,
                    },
                )
            )
        else:
            self.stdout.write("Skipping PostgreSQL prueba apply step. Add --apply-to-test to mutate the test DB.")

        steps.append(
            (
                "Generate final SQL",
                "_handle_generate_final_sql",
                {
                    "source": test_target,
                    "output": final_sql,
                    "batch_size": options["batch_size"],
                    "mode": options["mode"],
                    "truncate": options["truncate"],
                    "disable_triggers": options["disable_triggers_for_final_sql"],
                },
            )
        )
        return steps

    def _format_step(self, handler_name, kwargs):
        subcommand_map = {
            "_handle_validate_scope": "validate-scope",
            "_handle_generate_sqlite_sql": "generate-sqlite-sql",
            "_handle_apply_sql": "apply-sql",
            "_handle_generate_final_sql": "generate-final-sql",
        }
        subcommand = subcommand_map.get(handler_name, handler_name)
        parts = ["uv", "run", "python", "manage.py", "pg_prueba", subcommand]
        for key, value in kwargs.items():
            flag = "--" + key.replace("_", "-")
            if isinstance(value, bool):
                if value:
                    parts.append(flag)
                continue
            if value is None:
                continue
            parts.extend([flag, str(Path(value) if key in {"sqlite", "output", "sql"} else value)])
        return "+ " + " ".join(parts)
