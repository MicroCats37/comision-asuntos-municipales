"""
Clean or repair django-simple-history tables.

Usage:
    uv run python manage.py clean_simple_history --dry-run --settings=config.settings.development
    uv run python manage.py clean_simple_history --reset-sequences --settings=config.settings.development
    uv run python manage.py clean_simple_history --truncate --confirm --settings=config.settings.development
    uv run python manage.py clean_simple_history --table usuarios_historicalusuario --truncate --confirm --settings=config.settings.development
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = "List, repair sequences, or truncate django-simple-history tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            action="append",
            default=[],
            help=(
                "Specific historical table to target. Can be passed multiple times. "
                "When omitted, all public tables containing 'historical' are targeted."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show target tables and planned actions without writing changes.",
        )
        parser.add_argument(
            "--reset-sequences",
            action="store_true",
            help="Reset history_id sequences to MAX(history_id) + 1 without deleting rows.",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete rows from targeted historical tables and restart identities.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required with --truncate to confirm historical data deletion.",
        )

    def handle(self, *args, **options):
        tables = self._get_target_tables(options["table"])
        dry_run = options["dry_run"]
        reset_sequences = options["reset_sequences"]
        truncate = options["truncate"]
        confirm = options["confirm"]

        if truncate and not confirm:
            raise CommandError("--truncate deletes historical rows. Re-run with --confirm if that is intended.")

        if not reset_sequences and not truncate:
            dry_run = True

        if not tables:
            self.stdout.write(self.style.WARNING("No historical tables found."))
            return

        self.stdout.write("Target historical tables:")
        for table in tables:
            row_count = self._count_rows(table)
            self.stdout.write(f"  - {table}: {row_count} rows")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: no database changes were made."))
            if reset_sequences:
                self.stdout.write("Would reset history_id sequences.")
            if truncate:
                self.stdout.write("Would truncate tables and restart identities.")
            return

        with transaction.atomic():
            if truncate:
                self._truncate_tables(tables)
                self.stdout.write(self.style.SUCCESS("Historical tables truncated and identities restarted."))

            if reset_sequences:
                for table in tables:
                    self._reset_history_sequence(table)
                self.stdout.write(self.style.SUCCESS("Historical table sequences reset."))

    def _get_target_tables(self, requested_tables):
        with connection.cursor() as cursor:
            if requested_tables:
                placeholders = ", ".join(["%s"] * len(requested_tables))
                cursor.execute(
                    f"""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename IN ({placeholders})
                    ORDER BY tablename
                    """,
                    requested_tables,
                )
            else:
                cursor.execute(
                    """
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                      AND tablename LIKE %s
                    ORDER BY tablename
                    """,
                    ["%historical%"],
                )
            return [row[0] for row in cursor.fetchall()]

    def _count_rows(self, table):
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            return cursor.fetchone()[0]

    def _truncate_tables(self, tables):
        quoted_tables = ", ".join(f'"{table}"' for table in tables)
        with connection.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE")

    def _reset_history_sequence(self, table):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence(%s, 'history_id'),
                    (SELECT COALESCE(MAX(history_id), 0) + 1 FROM "{table}"),
                    false
                )
                """,
                [table],
            )
