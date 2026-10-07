import math
import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[5]
BACKEND_DIR = PROJECT_ROOT / "backend"
POSTGRES_PRUEBA_DIR = PROJECT_ROOT / "postgres_prueba"
DEFAULT_SQLITE_PATH = BACKEND_DIR / "db.sqlite3"
DEFAULT_SQLITE_SQL = POSTGRES_PRUEBA_DIR / "business_data.sql"
DEFAULT_OUTPUT_DIR = POSTGRES_PRUEBA_DIR / "outputs"
DEFAULT_TEST_DSN = "postgresql://cam_user:changeme@localhost:5433/cam_db_prueba"

DEFAULT_APPS = ("usuarios", "entidades", "liquidaciones", "finanzas")
SYSTEM_PREFIXES = ("django_", "auth_", "token_blacklist_", "django_q_")
AUTH_M2M_SUFFIXES = ("_groups", "_user_permissions")

BUSINESS_TABLES = [
    "usuarios_capitulo",
    "usuarios_especialidadingeniero",
    "usuarios_especialidadrevision",
    "usuarios_especialidadrevisioncapitulo",
    "entidades_ubigeodepartamento",
    "entidades_ubigeoprovincia",
    "entidades_ubigeodistrito",
    "entidades_municipalidad",
    "finanzas_uit",
    "finanzas_igv",
    "liquidaciones_tipoliquidacion",
    "finanzas_tasadelegado",
    "finanzas_escaladescuentoinspector",
    "finanzas_rangodescuentoinspector",
    "liquidaciones_liquidacioncodigo",
    "liquidaciones_tarifaliquidacionbase",
    "liquidaciones_tarifaporcentajeobra",
    "liquidaciones_tarifaporcategoriavisitas",
    "liquidaciones_tarifapormetrocuadrado",
    "liquidaciones_derechopormetrocuadrado",
    "liquidaciones_derechoporcentajeobra",
    "liquidaciones_liquidacionespecialidaddisponibles",
    "usuarios_usuario",
    "usuarios_perfilingeniero",
    "usuarios_ingenierohabilitacion",
    "entidades_entidad",
    "entidades_banco",
    "entidades_contacto",
    "entidades_contactobanco",
    "entidades_contactomunicipalidad",
    "entidades_alcalde",
    "entidades_gerenteurbano",
    "liquidaciones_delegado",
    "liquidaciones_inspector",
    "liquidaciones_proyectista",
    "liquidaciones_delegadooperacion",
    "liquidaciones_delegadooperacionperiodo",
    "liquidaciones_inspectoroperacion",
    "liquidaciones_inspectoroperacionperiodo",
    "liquidaciones_proyecto",
    "liquidaciones_liquidaciongeneral",
    "liquidaciones_liquidaciongeneral_especialidades_revisadas",
    "liquidaciones_liquidacionrelaciongrupo",
    "liquidaciones_liquidacionrelacionmiembro",
    "liquidaciones_liquidacioncontacto",
    "liquidaciones_liquidaciondocumentos",
    "liquidaciones_liquidacionproyectista",
    "liquidaciones_liquidacionedificacion",
    "liquidaciones_liquidacionporcentajeobra",
    "liquidaciones_liquidacionporcentajeobradetalle",
    "liquidaciones_liquidacionhabilitacionurbana",
    "liquidaciones_liquidacionpormetrocuadrado",
    "liquidaciones_liquidacioninspeccionobra",
    "liquidaciones_liquidacionporcategoriavisitas",
    "liquidaciones_liquidacionmecanicasuelos",
    "liquidaciones_liquidacionimpactovial",
    "liquidaciones_liquidaciontaludes",
    "liquidaciones_liquidaciondelegado",
    "liquidaciones_liquidacioninspector",
    "liquidaciones_liquidacioncomprobante",
    "finanzas_detallehonorariodelegado",
    "finanzas_detallehonorarioinspector",
    "finanzas_recibohonorariodelegado",
    "finanzas_recibohonorariodelegadomensual",
    "finanzas_recibohonorarioinspector",
    "finanzas_recibohonorarioinspectormensual",
    "finanzas_registropagoinspector",
    "finanzas_rhreparticionestacional",
    "finanzas_rhreparticionestacionaldelegado",
    "finanzas_rhreparticionestacionalcapitulo",
]


def default_final_sql() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"business_pg_batched_inserts_{timestamp}.sql"


def is_excluded_table(table_name: str) -> bool:
    lowered = table_name.lower()
    return (
        lowered.startswith(SYSTEM_PREFIXES)
        or lowered.endswith(AUTH_M2M_SUFFIXES)
        or "historical" in lowered
    )


def django_operational_tables(app_labels: tuple[str, ...]) -> set[str]:
    from django.apps import apps

    tables = set()
    for model in apps.get_models(include_auto_created=True):
        if model._meta.app_label not in app_labels:
            continue
        if model._meta.proxy:
            continue
        table_name = model._meta.db_table
        if is_excluded_table(table_name):
            continue
        tables.add(table_name)
    return tables


def sqlite_tables(sqlite_path: Path) -> set[str]:
    con = sqlite3.connect(sqlite_path)
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return {row[0] for row in cur.fetchall() if not is_excluded_table(row[0])}
    finally:
        con.close()


def postgres_tables(target_dsn: str) -> set[str]:
    import psycopg2

    con = psycopg2.connect(target_dsn)
    try:
        cur = con.cursor()
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            """
        )
        return {row[0] for row in cur.fetchall() if not is_excluded_table(row[0])}
    finally:
        con.close()


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def sql_literal(value, pg_type: str | None = None) -> str:
    if value is None:
        return "NULL"
    if pg_type == "boolean" or isinstance(value, bool):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, bytes):
        return "'\\x" + value.hex() + "'"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return "NULL"
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def sqlite_columns(cur, table: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({quote_ident(table)})")
    return [row[1] for row in cur.fetchall()]


def pg_columns_and_types(cur, table: str) -> dict[str, str]:
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def pg_columns(cur, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return [row[0] for row in cur.fetchall()]


def pg_primary_key_columns(cur, table: str) -> list[str]:
    cur.execute(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a
          ON a.attrelid = i.indrelid
         AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass
          AND i.indisprimary
        ORDER BY array_position(i.indkey, a.attnum)
        """,
        (f"public.{table}",),
    )
    return [row[0] for row in cur.fetchall()]


def conflict_clause(pk_cols: list[str], cols: list[str], mode: str) -> str:
    if mode == "insert":
        return ""
    if not pk_cols:
        return "\nON CONFLICT DO NOTHING"

    target = ", ".join(quote_ident(col) for col in pk_cols)
    update_cols = [col for col in cols if col not in pk_cols]
    if mode == "ignore" or not update_cols:
        return f"\nON CONFLICT ({target}) DO NOTHING"

    assignments = ", ".join(
        f"{quote_ident(col)} = EXCLUDED.{quote_ident(col)}" for col in update_cols
    )
    return f"\nON CONFLICT ({target}) DO UPDATE SET {assignments}"


def table_count(cur, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {quote_ident(table)}")
    return cur.fetchone()[0]


def chunks(items, size: int):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def find_safety_markers(sql_file: Path) -> list[str]:
    markers = []
    with sql_file.open("r", encoding="utf-8", errors="ignore") as handle:
        for line_number, line in enumerate(handle, start=1):
            upper_line = line.upper()
            if "TRUNCATE TABLE" in upper_line:
                markers.append(f"line {line_number}: TRUNCATE TABLE")
            if "SESSION_REPLICATION_ROLE" in upper_line:
                markers.append(f"line {line_number}: session_replication_role")
            if len(markers) >= 10:
                break
    return markers
