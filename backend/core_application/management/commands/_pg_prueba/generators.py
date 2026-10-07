import sqlite3
from pathlib import Path

from .common import (
    BUSINESS_TABLES,
    chunks,
    conflict_clause,
    pg_columns,
    pg_columns_and_types,
    pg_primary_key_columns,
    quote_ident,
    sql_literal,
    sqlite_columns,
    table_count,
)


def generate_sqlite_sql(
    *,
    sqlite_path: Path,
    target_dsn: str,
    output_path: Path,
    batch_size: int,
    mode: str,
    truncate: bool,
    disable_triggers: bool,
    stdout,
) -> int:
    import psycopg2

    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row
    pg = psycopg2.connect(target_dsn)
    try:
        sc = sq.cursor()
        pc = pg.cursor()
        total_rows = 0
        with output_path.open("w", encoding="utf-8", newline="\n") as out:
            out.write("-- Generated business-table INSERTs from backend/db.sqlite3\n")
            out.write("-- Do not edit manually unless you know exactly why.\n\n")
            out.write("BEGIN;\n")
            if disable_triggers:
                out.write("SET session_replication_role = replica;\n\n")
            else:
                out.write("\n")

            if truncate:
                quoted_tables = ", ".join(quote_ident(table) for table in BUSINESS_TABLES)
                out.write(f"TRUNCATE TABLE {quoted_tables} CASCADE;\n\n")

            for table in BUSINESS_TABLES:
                sqlite_cols = sqlite_columns(sc, table)
                pg_types = pg_columns_and_types(pc, table)
                pk_cols = pg_primary_key_columns(pc, table)
                common_cols = [col for col in sqlite_cols if col in pg_types]
                if not common_cols:
                    stdout.write(f"[SKIP] {table}: no common columns")
                    continue

                count = table_count(sc, table)
                total_rows += count
                stdout.write(f"[GEN ] {table}: {count} rows")
                out.write(f"-- {table}: {count} rows\n")

                if count == 0:
                    out.write("\n")
                    continue

                cols_sql = ", ".join(quote_ident(col) for col in common_cols)
                sc.execute("SELECT " + cols_sql + " FROM " + quote_ident(table))
                rows = sc.fetchall()
                for batch in chunks(rows, batch_size):
                    out.write(f"INSERT INTO {quote_ident(table)} ({cols_sql}) VALUES\n")
                    values_sql = []
                    for row in batch:
                        values = [sql_literal(row[col], pg_types[col]) for col in common_cols]
                        values_sql.append("  (" + ", ".join(values) + ")")
                    out.write(",\n".join(values_sql))
                    out.write(conflict_clause(pk_cols, common_cols, mode))
                    out.write(";\n")
                out.write("\n")

            if disable_triggers:
                out.write("\nSET session_replication_role = origin;\n")
            out.write("COMMIT;\n")

        stdout.write(f"Generated {output_path} with {total_rows} source rows")
        return total_rows
    finally:
        pg.close()
        sq.close()


def generate_final_sql(
    *,
    source_dsn: str,
    output_path: Path,
    batch_size: int,
    mode: str,
    truncate: bool,
    disable_triggers: bool,
    stdout,
) -> int:
    import psycopg2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    con = psycopg2.connect(source_dsn)
    try:
        cur = con.cursor()
        total_rows = 0
        with output_path.open("w", encoding="utf-8", newline="\n") as out:
            out.write("-- Generated batched INSERTs from postgres_prueba/cam_db_prueba\n")
            out.write("-- Source is PostgreSQL, not SQLite.\n\n")
            out.write("BEGIN;\n")
            if disable_triggers:
                out.write("SET session_replication_role = replica;\n\n")
            else:
                out.write("\n")

            if truncate:
                quoted_tables = ", ".join(quote_ident(table) for table in BUSINESS_TABLES)
                out.write(f"TRUNCATE TABLE {quoted_tables} CASCADE;\n\n")

            for table in BUSINESS_TABLES:
                cols = pg_columns(cur, table)
                pk_cols = pg_primary_key_columns(cur, table)
                count = table_count(cur, table)
                total_rows += count
                stdout.write(f"[GEN ] {table}: {count} rows")
                out.write(f"-- {table}: {count} rows\n")

                if count == 0:
                    out.write("\n")
                    continue

                cols_sql = ", ".join(quote_ident(col) for col in cols)
                cur.execute(f"SELECT {cols_sql} FROM {quote_ident(table)}")

                while True:
                    rows = cur.fetchmany(batch_size)
                    if not rows:
                        break
                    out.write(f"INSERT INTO {quote_ident(table)} ({cols_sql}) VALUES\n")
                    values_sql = []
                    for row in rows:
                        values = [sql_literal(value) for value in row]
                        values_sql.append("  (" + ", ".join(values) + ")")
                    out.write(",\n".join(values_sql))
                    out.write(conflict_clause(pk_cols, cols, mode))
                    out.write(";\n")
                out.write("\n")

            if disable_triggers:
                out.write("\nSET session_replication_role = origin;\n")
            out.write("COMMIT;\n")

        stdout.write(f"Generated {output_path} with {total_rows} source rows")
        return total_rows
    finally:
        con.close()
