import json
import os
import sqlite3
from pathlib import Path

import django
from django.apps import apps
from django.core.management import call_command
from django.core.management.color import no_style
from django.db import connection, transaction


EXCLUDED_MODELS = {
    "contenttypes.ContentType",
    "auth.Permission",
}


def table_columns(sqlite_cursor, table_name):
    sqlite_cursor.execute(f'PRAGMA table_info("{table_name}")')
    return {row[1] for row in sqlite_cursor.fetchall()}


def fetch_rows(sqlite_cursor, table_name, columns):
    quoted = ", ".join(f'"{column}"' for column in columns)
    sqlite_cursor.execute(f'SELECT {quoted} FROM "{table_name}"')
    for row in sqlite_cursor.fetchall():
        yield dict(zip(columns, row))


def import_model(sqlite_cursor, model):
    label = model._meta.label
    table_name = model._meta.db_table

    sqlite_cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    if sqlite_cursor.fetchone() is None:
        return {"model": label, "table": table_name, "status": "skipped", "reason": "missing_sqlite_table", "count": 0}

    sqlite_columns = table_columns(sqlite_cursor, table_name)
    fields = [field for field in model._meta.local_fields if field.column in sqlite_columns]
    missing_required = [
        field.column
        for field in model._meta.local_fields
        if field.column not in sqlite_columns and not field.null and not field.has_default() and not field.auto_created
    ]
    if missing_required:
        return {
            "model": label,
            "table": table_name,
            "status": "skipped",
            "reason": "missing_required_columns",
            "columns": missing_required,
            "count": 0,
        }

    columns = [field.column for field in fields]
    objects = []
    for row in fetch_rows(sqlite_cursor, table_name, columns):
        kwargs = {}
        for field in fields:
            kwargs[field.attname] = row[field.column]
        objects.append(model(**kwargs))

    if objects:
        model.objects.bulk_create(objects, batch_size=1000)

    return {"model": label, "table": table_name, "status": "loaded", "count": len(objects)}


def main():
    sqlite_path = Path(os.environ["SQLITE_IMPORT_PATH"])
    report_path = Path(os.environ.get("SQLITE_IMPORT_REPORT", "/tmp/sqlite_import_report.json"))

    if not sqlite_path.exists():
        raise SystemExit(f"SQLite file not found: {sqlite_path}")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    django.setup()

    call_command("flush", interactive=False, verbosity=1)

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_cursor = sqlite_conn.cursor()
    models = [
        model
        for model in apps.get_models(include_auto_created=False)
        if model._meta.label not in EXCLUDED_MODELS and model._meta.managed
    ]

    report = []
    loaded_models = []
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET session_replication_role = replica")
            for model in models:
                item = import_model(sqlite_cursor, model)
                report.append(item)
                if item["status"] == "loaded" and item["count"]:
                    loaded_models.append(model)
            with connection.cursor() as cursor:
                for sql in connection.ops.sequence_reset_sql(no_style(), loaded_models):
                    cursor.execute(sql)
                cursor.execute("SET session_replication_role = origin")
    finally:
        sqlite_conn.close()

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    loaded = sum(item["count"] for item in report if item["status"] == "loaded")
    skipped = [item for item in report if item["status"] == "skipped"]
    print(f"Loaded rows: {loaded}")
    print(f"Skipped models: {len(skipped)}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
