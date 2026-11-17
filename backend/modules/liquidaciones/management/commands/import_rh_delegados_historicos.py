"""
import_rh_delegados_historicos — Importa el dataset HISTORICO formal de RH Delegados
desde la fuente `core_application/seeds/historico/RH_EDIF.csv` (forma larga: una fila
por delegado-especialidad con la especialidad explicita).

Este comando NO reemplaza el dataset anterior: es un comando de CARGA sobre las tablas
de RH Delegados (las unicas que se vaciaron en la limpieza `limpiar_rh_delegados`). No
borra NADA: no toca `LiquidacionDelegado`, `DetalleHonorarioDelegado`, recibos,
`Delegado`, `DelegadoOperacion`, `DelegadoOperacionPeriodo` ni liquidaciones. Si una
asignacion ya existe, se omite (idempotente).

REGLAS DE ASOCIACION (una fila del CSV solo se asocia si cumple todas):
  1. Liquidacion: se resuelve EXCLUSIVAMENTE como `LiquidacionEdificacion` con
     `liquidacion__legacy = True` y `numero == NRO`. Nunca se adjunta a una liquidacion
     no legacy (IO) ni a una liquidacion "corriente". Si el NRO no existe o es
     ambiguo, la fila se omite y se reporta.
  2. Municipio y tipo de liquidacion: se HEREDAN de la liquidacion resuelta. El
     `CODPAGO` del CSV se usa solo como validacion/reporte: nunca sobrescribe el
     municipio de la liquidacion.
  3. Delegado: se resuelve por CIP normalizado (`zfill(6)`). Si no existe, se crea el
     `PerfilIngeniero` y el `Delegado` con el helper legacy-safe del proyecto
     (hidratacion por endpoint CIP con fallback a placeholder). Se reportan los
     contadores de creados / hidratados / placeholders.
  4. `delegado_operacion` es OPCIONAL: solo se busca como enriquecimiento contextual
     (delegado + municipalidad de la liquidacion + tipo + especialidad coincidente).
     Si no hay una operacion compatible e inequivoca, se persiste `NULL`. Nunca se
     crean, habilitan ni mutan operaciones ni periodos.
  5. Especialidad: viene de los alias del CSV (`ESPECIALIDAD_ALIAS`). Si la
     especialidad no existe en BD, la fila se omite y se reporta. Un desajuste de
     especialidad con la operacion NO salta la fila: deja la operacion en `NULL`.
  6. Llave de identidad del CSV: (NRO, CIP, NROORDEN). Las repeticiones se omiten
     como duplicados.
  7. Restriccion de BD: `UniqueConstraint(liquidacion, delegado, especialidad_revision)`.
     Dos filas distintas con la misma terna entran en conflicto: se conserva la
     primera (orden del CSV) y se omite la otra.

MODO:
  - Sin `--apply` (default): DRY-RUN. Solo lee, planifica e informa. Cero escrituras.
  - Con `--apply --confirm-destructive`: importa dentro de UNA sola transaccion
    (`transaction.atomic`). Cualquier error revierte todo el lote. La confirmacion
    sigue siendo obligatoria aunque el comando NO borre nada, para evitar cargar
    por accidente un dataset historico sobre una base ya migrada.

Lo que NO hace este comando:
  - No borra nada.
  - No crea `ReciboHonorarioDelegado` ni `ReciboHonorarioDelegadoMensual`.
  - No crea, habilita ni modifica `DelegadoOperacion` / `DelegadoOperacionPeriodo`.
  - No crea liquidaciones, proyectos ni municipalidades.

Uso:
    python manage.py import_rh_delegados_historicos
    python manage.py import_rh_delegados_historicos --apply --confirm-destructive
"""
import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.liquidaciones.domain.constants import DictamenRevision
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.resources import normalize_cip
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)

# Mapeo y normalizadores ya probados por la curacion existente (se reutilizan,
# no se reimplementan).
from .curar_rh_desde_excel import (
    ESPECIALIDAD_ALIAS,
    SEP,
    normalize_mes,
    normalize_nro_rh,
    normalize_periodo,
    parse_date,
    parse_dec,
    parse_int,
)

DEFAULT_RH_CSV = (
    Path(settings.BASE_DIR) / "core_application" / "seeds" / "historico" / "RH_EDIF.csv"
)
DEFAULT_REPORT_DIR = Path(settings.BASE_DIR).parent / "result" / "EDIF"
BATCH_SIZE = 1000

# Sentinel historica: el curado la descarta como "sin dato".
SENTINEL_DATE = date(1900, 1, 1)

# ── Motivos de omision (contrato de reporte) ───────────────────────────────────
SKIP_NRO_INVALIDO = "nro_invalido"
SKIP_CIP_INVALIDO = "cip_invalido"
SKIP_NRO_ORDEN_INVALIDO = "nro_orden_invalido"
SKIP_MES_INVALIDO = "mes_invalido"
SKIP_PERIODO_INVALIDO = "periodo_invalido"
SKIP_ESPECIALIDAD_INVALIDA = "especialidad_invalida"
SKIP_SIN_LIQUIDACION = "sin_liquidacion_legacy"
SKIP_LIQUIDACION_AMBIGUA = "liquidacion_ambigua"
SKIP_ESPECIALIDAD_INEXISTENTE = "especialidad_inexistente"
SKIP_SIN_DELEGADO = "sin_delegado_cip"
SKIP_DUPLICADO = "duplicado_csv"
SKIP_CONFLICTO = "conflicto_constraint"
SKIP_YA_EXISTENTE = "ya_existente"

SKIP_LABELS = {
    SKIP_NRO_INVALIDO: "Saltadas - NRO no numerico",
    SKIP_CIP_INVALIDO: "Saltadas - CIP no numerico",
    SKIP_NRO_ORDEN_INVALIDO: "Saltadas - NROORDEN invalido o cero",
    SKIP_MES_INVALIDO: "Saltadas - MES invalido o vacio",
    SKIP_PERIODO_INVALIDO: "Saltadas - PERIODO invalido o vacio",
    SKIP_ESPECIALIDAD_INVALIDA: "Saltadas - ESPECIALIDAD vacia o NULL",
    SKIP_SIN_LIQUIDACION: "Saltadas - NRO sin LiquidacionEdificacion legacy",
    SKIP_LIQUIDACION_AMBIGUA: "Saltadas - NRO ambiguo (varias liquidaciones legacy)",
    SKIP_ESPECIALIDAD_INEXISTENTE: "Saltadas - especialidad inexistente en BD",
    SKIP_SIN_DELEGADO: "Saltadas - sin delegado (CIP no resoluble)",
    SKIP_DUPLICADO: "Duplicados CSV (NRO, CIP, NROORDEN)",
    SKIP_CONFLICTO: "Conflictos de constraint (liquidacion+delegado+especialidad)",
    SKIP_YA_EXISTENTE: "Ya existentes (idempotente, sin volver a crear)",
}

# ── Estados del enriquecimiento contextual de `delegado_operacion` ─────────────
OPERACION_LINK = "con_operacion"
OPERACION_NULA = "sin_operacion"
OPERACION_AMBIGUA = "operacion_ambigua"
OPERACION_ESPECIALIDAD = "operacion_especialidad_distinta"

OPERACION_LABELS = {
    OPERACION_LINK: "Asignadas con delegado_operacion",
    OPERACION_NULA: "Asignadas con delegado_operacion NULL (sin operacion compatible)",
    OPERACION_AMBIGUA: "Asignadas con delegado_operacion NULL (operacion ambigua)",
    OPERACION_ESPECIALIDAD: "Asignadas con delegado_operacion NULL (especialidad distinta)",
}

# ── Avisos de calidad de datos (no saltan la fila) ───────────────────────────
WARN_CODPAGO = "codpago_no_coincide"


# ── Helpers puros (testeables sin DB) ─────────────────────────────────────────


def strip_accents(value: str) -> str:
    """Quita acentos sin alterar el resto del texto."""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(value)) if unicodedata.category(c) != "Mn"
    )


def normalize_dictamen(raw) -> str | None:
    """DICTAMEN del CSV -> valor de `DictamenRevision` (o None si no aplica)."""
    text = str(raw or "").strip().upper()
    if not text or text in ("NULL", "NONE"):
        return None
    candidate = re.sub(r"_+", "_", text.replace(".", "").replace(" ", "_")).strip("_")
    valid = {value for value, _ in DictamenRevision.choices}
    return candidate if candidate in valid else None


def canonical_especialidad(raw) -> str | None:
    """ESPECIALIDAD del CSV -> nombre canonico de `EspecialidadRevision`."""
    text = str(raw or "").strip()
    if not text or text.upper() in ("NULL", "NONE"):
        return None
    return ESPECIALIDAD_ALIAS.get(strip_accents(text.upper()))


def build_especialidad_index(especialidades) -> dict:
    """EspecialidadRevision -> {nombre normalizado: id}."""
    index = {}
    for esp in especialidades:
        index[strip_accents(esp.nombre.upper())] = esp.id
    return index


def resolve_especialidad_id(nombre_canonico: str, index: dict):
    """Resuelve el id de `EspecialidadRevision` desde el nombre canonico.

    Fallback por prefijo para tolerar diferencias de nombre entre BD y CSV
    (p.ej. "Ingenieria Electrica y Mecanica" vs "... y Mecanica Electrica").
    """
    key = strip_accents(str(nombre_canonico or "").upper())
    if not key:
        return None
    if key in index:
        return index[key]
    for name_key in sorted(index):
        if name_key.startswith(key) or key.startswith(name_key):
            return index[name_key]
    return None


def resolve_operacion(candidatos, tipo_liquidacion_id, especialidad_id):
    """Elige la `DelegadoOperacion` compatible como enriquecimiento contextual.

    `candidatos` es la lista de operaciones del delegado para la municipalidad de la
    liquidacion resuelta. Cada candidata trae `id`, `tipo_liquidacion_id` y
    `especialidad_revision_id`.

    Devuelve `(operacion_id | None, estado)`:
      - coincidencia exacta de `tipo_liquidacion` tiene prioridad;
      - una operacion con `tipo_liquidacion` NULL acts como wildcard;
      - la especialidad debe coincidir con la del CSV;
      - exacta + wildcard a la vez, o varias candidatas, es ambiguedad -> NULL.
    """
    exactas = [
        op
        for op in candidatos
        if op["tipo_liquidacion_id"] is not None
        and op["tipo_liquidacion_id"] == tipo_liquidacion_id
    ]
    wildcards = [op for op in candidatos if op["tipo_liquidacion_id"] is None]

    match_exactas = [op for op in exactas if op["especialidad_revision_id"] == especialidad_id]
    match_wildcards = [
        op for op in wildcards if op["especialidad_revision_id"] == especialidad_id
    ]

    if len(match_exactas) == 1 and not match_wildcards:
        return match_exactas[0]["id"], OPERACION_LINK
    if len(match_exactas) == 1 and match_wildcards:
        return None, OPERACION_AMBIGUA
    if not match_exactas and len(match_wildcards) == 1:
        return match_wildcards[0]["id"], OPERACION_LINK
    if not match_exactas and len(match_wildcards) > 1:
        return None, OPERACION_AMBIGUA

    # No hubo coincidencia por especialidad: se distingue "no existe operacion"
    # de "existe pero con otra especialidad".
    if exactas or wildcards:
        return None, OPERACION_ESPECIALIDAD
    return None, OPERACION_NULA


# ── Modelo de datos del proceso ────────────────────────────────────────────────


@dataclass
class RhRow:
    """Fila del CSV normalizada y lista para asociar."""

    linea: int
    nro: int
    cip: str
    nro_orden: str
    especialidad_nombre: str
    codpago: str = ""
    mes: int | None = None
    periodo: int | None = None
    dictamen: str | None = None
    fecha_presentacion: date | None = None
    fecha_revision: date | None = None
    imp_bruto: Decimal = Decimal("0")
    aporte_codemu: Decimal = Decimal("0")
    fondo_comun: Decimal = Decimal("0")
    neto_honorario: Decimal = Decimal("0")
    renta_cip: Decimal = Decimal("0")

    @property
    def key_csv(self) -> tuple:
        """Llave de identidad natural de la fila: (NRO, CIP, NROORDEN)."""
        return (self.nro, self.cip, self.nro_orden)


@dataclass
class PlanEntry:
    """Fila asociada: liquidacion + delegado + operacion (opcional) + especialidad."""

    row: RhRow
    liquidacion_id: object
    especialidad_id: object
    delegado_id: object | None = None
    delegacion_pendiente: bool = False
    sin_delegado: bool = False
    operacion_id: object | None = None
    operacion_estado: str = OPERACION_NULA


@dataclass
class ImportReport:
    """Contadores del proceso (contrato de salida del comando)."""

    filas_leidas: int = 0
    filas_invalidas: int = 0
    importadas: int = 0
    importadas_con_importe_cero: int = 0
    omitidas: dict = field(default_factory=lambda: defaultdict(int))
    avisos: dict = field(default_factory=lambda: defaultdict(int))
    operacion_estados: dict = field(default_factory=lambda: defaultdict(int))
    delegados_creados: int = 0
    perfiles_creados: int = 0
    perfiles_hidratados: int = 0
    perfiles_placeholder: int = 0
    detalles_creados: int = 0


def normalize_row(raw: dict, linea: int):
    """Fila cruda del CSV -> (RhRow | None, motivo_de_invalidez)."""
    nro = parse_int(raw.get("NRO"))
    if nro is None:
        return None, SKIP_NRO_INVALIDO

    cip = normalize_cip(raw.get("CIP"))
    if not cip:
        return None, SKIP_CIP_INVALIDO

    nro_orden = normalize_nro_rh(raw.get("NROORDEN"))
    if not nro_orden or int(nro_orden) <= 0:
        return None, SKIP_NRO_ORDEN_INVALIDO

    especialidad = canonical_especialidad(raw.get("ESPECIALIDAD"))
    if not especialidad:
        return None, SKIP_ESPECIALIDAD_INVALIDA

    mes_raw = normalize_mes(raw.get("MES"))
    mes = int(mes_raw) if mes_raw and mes_raw.isdigit() and 1 <= int(mes_raw) <= 12 else None
    if mes is None:
        return None, SKIP_MES_INVALIDO

    periodo_raw = normalize_periodo(raw.get("PERIODO"))
    periodo = int(periodo_raw) if periodo_raw and len(periodo_raw) == 4 else None
    if periodo is None or periodo <= 0:
        return None, SKIP_PERIODO_INVALIDO

    fecha_presentacion = parse_date(raw.get("FECHAPRES"))
    if fecha_presentacion == SENTINEL_DATE:
        fecha_presentacion = None
    fecha_revision = parse_date(raw.get("FECHAREVI"))
    if fecha_revision == SENTINEL_DATE:
        fecha_revision = None

    neto = parse_dec(raw.get("NETOHONORA"))
    if not neto:
        neto = parse_dec(raw.get("HONORARIO"))

    return (
        RhRow(
            linea=linea,
            nro=nro,
            cip=cip,
            nro_orden=nro_orden,
            especialidad_nombre=especialidad,
            codpago=str(raw.get("CODPAGO") or "").strip().upper(),
            mes=mes,
            periodo=periodo,
            dictamen=normalize_dictamen(raw.get("DICTAMEN")),
            fecha_presentacion=fecha_presentacion,
            fecha_revision=fecha_revision,
            imp_bruto=parse_dec(raw.get("IMPBRUTO")),
            aporte_codemu=parse_dec(raw.get("APORCODEMU")),
            fondo_comun=parse_dec(raw.get("FONDOCOMUN")),
            neto_honorario=neto,
            renta_cip=parse_dec(raw.get("RENTACIP")),
        ),
        None,
    )


def read_rh_rows(path: Path, limit: int | None = None):
    """Lee el CSV formal -> (filas validas, filas invalidas con su motivo)."""
    rows: list[RhRow] = []
    invalid: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=SEP)
        for linea, raw in enumerate(reader, start=2):
            if limit is not None and len(rows) >= limit:
                break
            row, motivo = normalize_row(raw, linea)
            if row is None:
                invalid.append(
                    {
                        "linea": linea,
                        "nro": str(raw.get("NRO", "")).strip(),
                        "cip": str(raw.get("CIP", "")).strip(),
                        "nro_orden": str(raw.get("NROORDEN", "")).strip(),
                        "especialidad": str(raw.get("ESPECIALIDAD", "")).strip(),
                        "motivo": motivo,
                    }
                )
            else:
                rows.append(row)
    return rows, invalid


# ── Comando ────────────────────────────────────────────────────────────────────


class Command(BaseCommand):
    help = (
        "Importa el dataset historico formal de RH Delegados desde RH_EDIF.csv. "
        "DRY-RUN por defecto; --apply --confirm-destructive importa en una transaccion. "
        "No borra nada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--rh-csv",
            type=str,
            default=str(DEFAULT_RH_CSV),
            help=f"Path al RH_EDIF.csv formal (default: {DEFAULT_RH_CSV})",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Ejecutar la importacion (default: dry-run).",
        )
        parser.add_argument(
            "--confirm-destructive",
            action="store_true",
            help=(
                "Confirmacion explicita. Sin este flag, --apply aborta. Aunque el "
                "comando no borra nada, la confirmacion evita cargar por accidente "
                "un dataset historico sobre una base ya migrada."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Procesa solo las primeras N filas validas del CSV (smoke test).",
        )
        parser.add_argument(
            "--no-cip-endpoint",
            action="store_true",
            help=(
                "No consultar el endpoint CIP: los CIP nuevos se crean directamente "
                "como placeholder (mismo criterio del importador legacy de "
                "habilitacion urbana)."
            ),
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Path del reporte CSV de filas omitidas (default: result/EDIF/...).",
        )

    # ── handle ────────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        apply = bool(options["apply"])
        confirm = bool(options["confirm_destructive"])
        rh_path = Path(options["rh_csv"])

        if apply and not confirm:
            raise CommandError(
                "--apply requiere --confirm-destructive: la carga del dataset "
                "historico de RH Delegados debe ser explicita (aunque el comando no "
                "borre nada)."
            )
        if not rh_path.exists():
            raise CommandError(f"No existe el CSV de RH: {rh_path}")

        report = ImportReport()

        self.stdout.write(self.style.NOTICE("=" * 74))
        self.stdout.write(
            self.style.NOTICE(
                "import_rh_delegados_historicos — "
                + ("APPLY (importacion)" if apply else "DRY-RUN (sin escrituras)")
            )
        )
        self.stdout.write(self.style.NOTICE("=" * 74))
        self.stdout.write(f"  CSV:               {rh_path}")
        self.stdout.write(
            f"  Modo:              {'APPLY' if apply else 'DRY-RUN'} "
            f"(confirmacion destructiva: {'si' if confirm else 'no'})"
        )
        self.stdout.write("")

        # ── 1. Lectura del CSV ────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("[1/5] Leyendo RH_EDIF.csv..."))
        filas, invalidas = read_rh_rows(rh_path, limit=options.get("limit"))
        report.filas_leidas = len(filas) + len(invalidas)
        report.filas_invalidas = len(invalidas)
        self.stdout.write(f"  Filas leidas:       {report.filas_leidas}")
        self.stdout.write(f"  Filas invalidas:    {report.filas_invalidas}")
        self.stdout.write(f"  Filas validas:      {len(filas)}")
        self.stdout.write("")

        # ── 2. Contexto de BD (solo lectura) ─────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("[2/5] Cargando contexto de BD..."))
        indexes = self._cargar_indexes(filas)
        especialidad_ids = build_especialidad_index(EspecialidadRevision.objects.all())
        self.stdout.write(
            f"  Liquidaciones legacy (NRO): {len(indexes['liquidaciones'])}"
        )
        self.stdout.write(f"  Delegados (CIP):              {len(indexes['delegados'])}")
        self.stdout.write(
            f"  Grupos (delegado, muni):       {len(indexes['operaciones'])}"
        )
        self.stdout.write(f"  Especialidades:               {len(especialidad_ids)}")
        self.stdout.write(f"  Asignaciones ya existentes:    {len(indexes['existentes'])}")
        self.stdout.write("")

        # ── 3. Planificacion ──────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("[3/5] Planificando..."))
        plan, omitidas, detalle_omitidas, avisos_detalle = self._planificar(
            filas, indexes, especialidad_ids
        )
        for motivo, cantidad in omitidas.items():
            report.omitidas[motivo] = cantidad
        # Las filas invalidas del CSV tambien se reportan por motivo.
        for fila_invalida in invalidas:
            report.omitidas[fila_invalida["motivo"]] += 1
        report.avisos[WARN_CODPAGO] = len(avisos_detalle)
        report.importadas = len(plan)
        report.importadas_con_importe_cero = sum(
            1 for entry in plan if not entry.row.imp_bruto and not entry.row.neto_honorario
        )
        for entry in plan:
            report.operacion_estados[entry.operacion_estado] += 1
        self.stdout.write(f"  Filas a asociar:    {len(plan)}")
        self.stdout.write("")

        # ── 4. Importacion (una sola transaccion) ────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("[4/5] Importacion..."))
        if not apply:
            self.stdout.write(self.style.WARNING("  [DRY-RUN] No se ejecuta ninguna escritura."))
            self.stdout.write(
                f"  [DRY-RUN] LiquidacionDelegado a crear:     {len(plan)}"
            )
            self.stdout.write(
                f"  [DRY-RUN] DetalleHonorarioDelegado a crear: {len(plan)}"
            )
            self.stdout.write(
                f"  [DRY-RUN] Delegados a crear:                "
                f"{len({e.row.cip for e in plan if e.delegacion_pendiente})}"
            )
        else:
            with transaction.atomic():
                self._asegurar_delegados(
                    plan, report, use_endpoint=not options["no_cip_endpoint"]
                )
                report.detalles_creados = self._importar(plan)
                report.importadas = sum(1 for entry in plan if not entry.sin_delegado)
            self.stdout.write(self.style.SUCCESS("  Transaccion confirmada."))

        # ── 5. Reporte ────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("[5/5] Reporte..."))
        self._imprimir_resumen(report)
        self._escribir_reporte(detalle_omitidas, invalidas, avisos_detalle, options)

        if apply:
            self.stdout.write(
                self.style.SUCCESS("Importacion historica de RH Delegados completada.")
            )
        else:
            self.stdout.write(
                self.style.WARNING("DRY-RUN — no se modifico la base de datos.")
            )

    # ── Paso 2: contexto de BD ───────────────────────────────────────────────

    def _cargar_indexes(self, filas) -> dict:
        """Carga en memoria los indices necesarios para resolver cada fila."""
        liquidaciones: dict = defaultdict(list)
        numeros = {f.nro for f in filas}
        if numeros:
            queryset = (
                LiquidacionEdificacion.objects.filter(
                    liquidacion__legacy=True,
                    numero__gte=min(numeros),
                    numero__lte=max(numeros),
                )
                .values(
                    "numero",
                    "liquidacion_id",
                    "liquidacion__municipalidad_id",
                    "liquidacion__tipo_liquidacion_id",
                    "liquidacion__municipalidad__codigo",
                )
            )
            for item in queryset:
                liquidaciones[item["numero"]].append(
                    {
                        "liquidacion_id": item["liquidacion_id"],
                        "municipalidad_id": item["liquidacion__municipalidad_id"],
                        "tipo_liquidacion_id": item["liquidacion__tipo_liquidacion_id"],
                        "municipalidad_codigo": item["liquidacion__municipalidad__codigo"] or "",
                    }
                )

        delegados: dict = {}
        for item in Delegado.objects.values("id", "perfil_ingeniero__cip"):
            cip = normalize_cip(item["perfil_ingeniero__cip"])
            if cip:
                delegados[cip] = item["id"]

        operaciones: dict = defaultdict(list)
        for operacion in DelegadoOperacion.objects.values(
            "id",
            "delegado_id",
            "municipalidad_id",
            "tipo_liquidacion_id",
            "especialidad_revision_id",
        ):
            operaciones[(operacion["delegado_id"], operacion["municipalidad_id"])].append(
                operacion
            )

        # Asignaciones ya existentes (idempotencia): (liquidacion, delegado, especialidad).
        existentes: dict = {}
        for item in LiquidacionDelegado.objects.values(
            "id", "liquidacion_id", "delegado_id", "especialidad_revision_id"
        ):
            existentes[
                (
                    item["liquidacion_id"],
                    item["delegado_id"],
                    item["especialidad_revision_id"],
                )
            ] = item["id"]

        return {
            "liquidaciones": liquidaciones,
            "delegados": delegados,
            "operaciones": operaciones,
            "existentes": existentes,
        }

    # ── Paso 3: planificacion ────────────────────────────────────────────────

    def _planificar(self, filas, indexes, especialidad_ids):
        """Resuelve cada fila: plan de importacion + detalle de omisiones."""
        plan: list[PlanEntry] = []
        omitidas: dict = defaultdict(int)
        detalle_omitidas: list[dict] = []
        avisos: list[dict] = []

        vistos_csv: set = set()
        vistos_constraint: set = set()

        for fila in filas:
            motivo = None
            liquidacion = None
            especialidad_id = None
            operacion_id = None
            operacion_estado = OPERACION_NULA
            delegado_id = None
            delegacion_pendiente = False
            codpago_bd = ""

            if fila.key_csv in vistos_csv:
                motivo = SKIP_DUPLICADO
            else:
                vistos_csv.add(fila.key_csv)

                candidatas = indexes["liquidaciones"].get(fila.nro, [])
                if not candidatas:
                    motivo = SKIP_SIN_LIQUIDACION
                elif len(candidatas) > 1:
                    motivo = SKIP_LIQUIDACION_AMBIGUA
                else:
                    liquidacion = candidatas[0]
                    codpago_bd = liquidacion["municipalidad_codigo"]

                    # CODPAGO: solo validacion/reporte. Nunca sobrescribe el
                    # municipio heredado de la liquidacion.
                    if fila.codpago and codpago_bd and fila.codpago != codpago_bd:
                        avisos.append(
                            {
                                "linea": fila.linea,
                                "nro": fila.nro,
                                "cip": fila.cip,
                                "nro_orden": fila.nro_orden,
                                "especialidad": fila.especialidad_nombre,
                                "codpago_csv": fila.codpago,
                                "codpago_bd": codpago_bd,
                                "motivo": WARN_CODPAGO,
                            }
                        )

                    especialidad_id = resolve_especialidad_id(
                        fila.especialidad_nombre, especialidad_ids
                    )
                    if especialidad_id is None:
                        motivo = SKIP_ESPECIALIDAD_INEXISTENTE
                    else:
                        delegado_id = indexes["delegados"].get(fila.cip)
                        if delegado_id is None:
                            # El delegado se crea en la fase de escritura
                            # (en dry-run no se escribe nada).
                            delegacion_pendiente = True
                        else:
                            operacion_id, operacion_estado = resolve_operacion(
                                indexes["operaciones"].get(
                                    (delegado_id, liquidacion["municipalidad_id"]), ()
                                ),
                                liquidacion["tipo_liquidacion_id"],
                                especialidad_id,
                            )

            if motivo is None:
                # Clave del constraint de BD: (liquidacion, delegado, especialidad).
                # Si el delegado todavia no existe, se usa el CIP como clave
                # provisoria (un delegado nuevo es 1:1 con su CIP).
                ref_delegado = delegado_id if delegado_id is not None else f"CIP:{fila.cip}"
                key_constraint = (
                    liquidacion["liquidacion_id"],
                    ref_delegado,
                    especialidad_id,
                )
                if key_constraint in indexes["existentes"] or key_constraint in vistos_constraint:
                    motivo = (
                        SKIP_YA_EXISTENTE
                        if key_constraint in indexes["existentes"]
                        else SKIP_CONFLICTO
                    )
                else:
                    vistos_constraint.add(key_constraint)

            if motivo is None:
                plan.append(
                    PlanEntry(
                        row=fila,
                        liquidacion_id=liquidacion["liquidacion_id"],
                        especialidad_id=especialidad_id,
                        delegado_id=delegado_id,
                        delegacion_pendiente=delegacion_pendiente,
                        operacion_id=operacion_id,
                        operacion_estado=operacion_estado,
                    )
                )
            else:
                omitidas[motivo] += 1
                detalle_omitidas.append(
                    {
                        "linea": fila.linea,
                        "nro": fila.nro,
                        "cip": fila.cip,
                        "nro_orden": fila.nro_orden,
                        "especialidad": fila.especialidad_nombre,
                        "codpago_csv": fila.codpago,
                        "codpago_bd": codpago_bd,
                        "motivo": motivo,
                    }
                )

        return plan, omitidas, detalle_omitidas, avisos

    # ── Paso 4: escritura ────────────────────────────────────────────────────

    def _asegurar_delegados(self, plan, report: ImportReport, use_endpoint: bool) -> None:
        """Crea los `PerfilIngeniero`/`Delegado` que falten (helper legacy-safe).

        Devuelve el conjunto de CIPs que quedaron sin delegado resoluble.
        """
        por_cip: dict = defaultdict(list)
        for entry in plan:
            if entry.delegacion_pendiente:
                por_cip[entry.row.cip].append(entry)

        for cip in sorted(por_cip):
            perfil, status = self._ensure_perfil_ingeniero_by_cip(cip, use_endpoint=use_endpoint)
            if perfil is None:
                report.omitidas[SKIP_SIN_DELEGADO] += len(por_cip[cip])
                for entry in por_cip[cip]:
                    entry.delegacion_pendiente = False
                    entry.sin_delegado = True
                continue
            if status == "CREADO_DESDE_CIP":
                report.perfiles_hidratados += 1
                report.perfiles_creados += 1
            elif status == "CREADO_PLACEHOLDER":
                report.perfiles_placeholder += 1
                report.perfiles_creados += 1
            elif status == "ACTUALIZADO_DESDE_CIP":
                report.perfiles_hidratados += 1
            delegado, _ = Delegado.objects.get_or_create(perfil_ingeniero=perfil)
            report.delegados_creados += 1
            for entry in por_cip[cip]:
                entry.delegado_id = delegado.id
                entry.delegacion_pendiente = False

    def _ensure_perfil_ingeniero_by_cip(
        self, cip: str, use_endpoint: bool = True
    ) -> tuple[PerfilIngeniero | None, str]:
        """Helper legacy-safe: resuelve o crea el `PerfilIngeniero` de un CIP.

        Mismo comportamiento que el importador legacy del proyecto
        (`import_legacy_edificaciones._ensure_perfil_ingeniero_by_cip`): primero
        busca el perfil local; si no existe, intenta hidratarlo desde el endpoint
        CIP y, si el endpoint no devuelve datos, cae a un perfil placeholder
        minimo marcado con `CIP <cip>` para no bloquear la importacion.
        """
        local = PerfilIngeniero.objects.filter(cip=cip).first()
        if local is not None:
            return local, "YA_EXISTE"

        if not use_endpoint:
            try:
                perfil, _ = PerfilIngeniero.objects.get_or_create(
                    cip=cip,
                    defaults={
                        "nombres": f"CIP {cip}",
                        "apellido_paterno": "CIP",
                        "apellido_materno": cip,
                    },
                )
                return perfil, "CREADO_PLACEHOLDER"
            except Exception:  # noqa: BLE001
                return None, "ERROR"

        from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import (
            PerfilIngenieroCoreService,
        )

        service = PerfilIngenieroCoreService()
        perfil, status = service.hydrate_perfil_from_cip(cip, dry_run=False)
        if perfil is not None:
            return perfil, status

        try:
            perfil, _ = PerfilIngeniero.objects.get_or_create(
                cip=cip,
                defaults={
                    "nombres": f"CIP {cip}",
                    "apellido_paterno": "CIP",
                    "apellido_materno": cip,
                },
            )
            return perfil, "CREADO_PLACEHOLDER"
        except Exception:  # noqa: BLE001
            return None, "ERROR"

    def _importar(self, plan) -> int:
        """Crea los `LiquidacionDelegado` y sus `DetalleHonorarioDelegado`."""
        detalles_creados = 0
        importables = [entry for entry in plan if not entry.sin_delegado]

        for inicio in range(0, len(importables), BATCH_SIZE):
            lote = importables[inicio:inicio + BATCH_SIZE]
            asignaciones = []
            for entry in lote:
                fila = entry.row
                asignaciones.append(
                    LiquidacionDelegado(
                        liquidacion_id=entry.liquidacion_id,
                        delegado_id=entry.delegado_id,
                        especialidad_revision_id=entry.especialidad_id,
                        delegado_operacion_id=entry.operacion_id,
                        periodo=fila.periodo,
                        mes=fila.mes,
                        dictamen_revision=fila.dictamen,
                        fecha_presentacion=fila.fecha_presentacion,
                        fecha_revision=fila.fecha_revision,
                        numero_rh=fila.nro_orden,
                        creado_por_rh=False,
                    )
                )

            LiquidacionDelegado.objects.bulk_create(asignaciones, batch_size=BATCH_SIZE)

            detalles = []
            for asignacion, entry in zip(asignaciones, lote):
                fila = entry.row
                detalles.append(
                    DetalleHonorarioDelegado(
                        recibo_mensual=None,
                        liquidacion_delegado_id=asignacion.id,
                        imp_bruto=fila.imp_bruto,
                        sub_total=None,
                        renta_cip=fila.renta_cip,
                        aporte_codemu=fila.aporte_codemu,
                        fondo_comun=fila.fondo_comun,
                        neto_honorario=fila.neto_honorario,
                        tasa_delegado=None,
                    )
                )
            DetalleHonorarioDelegado.objects.bulk_create(detalles, batch_size=BATCH_SIZE)
            detalles_creados += len(detalles)

        return detalles_creados

    # ── Reportes ─────────────────────────────────────────────────────────────

    def _imprimir_resumen(self, report: ImportReport) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("-" * 74))
        self.stdout.write(self.style.NOTICE("RESUMEN"))
        self.stdout.write(self.style.NOTICE("-" * 74))
        self.stdout.write(f"  Filas leidas (CSV):                {report.filas_leidas}")
        self.stdout.write(f"  Filas invalidas:                   {report.filas_invalidas}")
        self.stdout.write(f"  Importadas (LiquidacionDelegado):  {report.importadas}")
        self.stdout.write(f"  Importadas (DetalleHonorario):     {report.importadas}")
        self.stdout.write(f"    - con importe cero:              {report.importadas_con_importe_cero}")
        self.stdout.write(f"  Detalles creados:                  {report.detalles_creados}")
        self.stdout.write(f"  Delegados creados:                 {report.delegados_creados}")
        self.stdout.write(f"  Perfiles creados:                  {report.perfiles_creados}")
        self.stdout.write(f"    - hidratados desde CIP:          {report.perfiles_hidratados}")
        self.stdout.write(f"    - placeholder:                   {report.perfiles_placeholder}")
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("  Enriquecimiento de delegado_operacion:"))
        for estado in (
            OPERACION_LINK,
            OPERACION_NULA,
            OPERACION_AMBIGUA,
            OPERACION_ESPECIALIDAD,
        ):
            self.stdout.write(
                f"    {OPERACION_LABELS[estado]}: {report.operacion_estados[estado]}"
            )
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("  Omitidas:"))
        for motivo in (
            SKIP_NRO_INVALIDO,
            SKIP_CIP_INVALIDO,
            SKIP_NRO_ORDEN_INVALIDO,
            SKIP_MES_INVALIDO,
            SKIP_PERIODO_INVALIDO,
            SKIP_ESPECIALIDAD_INVALIDA,
            SKIP_SIN_LIQUIDACION,
            SKIP_LIQUIDACION_AMBIGUA,
            SKIP_ESPECIALIDAD_INEXISTENTE,
            SKIP_SIN_DELEGADO,
        ):
            self.stdout.write(f"    {SKIP_LABELS[motivo]}: {report.omitidas[motivo]}")
        self.stdout.write(f"    {SKIP_LABELS[SKIP_DUPLICADO]}: {report.omitidas[SKIP_DUPLICADO]}")
        self.stdout.write(f"    {SKIP_LABELS[SKIP_CONFLICTO]}: {report.omitidas[SKIP_CONFLICTO]}")
        self.stdout.write(
            f"    {SKIP_LABELS[SKIP_YA_EXISTENTE]}: {report.omitidas[SKIP_YA_EXISTENTE]}"
        )
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("  Avisos de calidad de datos (no omiten la fila):"))
        self.stdout.write(
            f"    CODPAGO del CSV distinto del municipio de la liquidacion: "
            f"{report.avisos[WARN_CODPAGO]}"
        )
        self.stdout.write("")
        self.stdout.write(
            "  Nota: las filas creadas con bulk_create no generan registro en "
            "simple_history."
        )
        self.stdout.write(self.style.NOTICE("-" * 74))

    def _escribir_reporte(self, omitidas_detalle, invalidas, avisos_detalle, options) -> None:
        out_path = options.get("output")
        if not out_path:
            ts = timezone.localtime().strftime("%Y%m%d_%H%M%S")
            modo = "apply" if options.get("apply") else "dryrun"
            out_path = DEFAULT_REPORT_DIR / f"import_rh_delegados_historicos_{modo}_{ts}.csv"
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        header = [
            "linea",
            "nro",
            "cip",
            "nro_orden",
            "especialidad",
            "codpago_csv",
            "codpago_bd",
            "motivo",
        ]
        with out_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=SEP)
            writer.writerow(header)
            for fila in omitidas_detalle:
                writer.writerow([fila.get(columna, "") for columna in header])
            for fila in invalidas:
                writer.writerow(
                    [
                        fila.get("linea", ""),
                        fila.get("nro", ""),
                        fila.get("cip", ""),
                        fila.get("nro_orden", ""),
                        fila.get("especialidad", ""),
                        "",
                        "",
                        fila.get("motivo", ""),
                    ]
                )
        self.stdout.write(f"  Reporte de omitidas: {out_path}")

        avisos_path = out_path.with_name(f"{out_path.stem}.avisos.csv")
        with avisos_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=SEP)
            writer.writerow(header)
            for fila in avisos_detalle:
                writer.writerow([fila.get(columna, "") for columna in header])
        self.stdout.write(f"  Reporte de avisos:    {avisos_path}")
