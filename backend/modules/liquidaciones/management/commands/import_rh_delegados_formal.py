"""
import_rh_delegados_formal — Recarga formal de los RH Delegados desde RH_EDIF.csv.

DESTRUCTIVO e idempotente. Reemplaza el dataset historico de RH Delegados
(derivado del importador legacy `import_legacy_edificaciones`, que deducía la
especialidad de la posicion del "slot") por el dataset formal de la fuente
`core_application/seeds/historico/RH_EDIF.csv` (forma larga: una fila por
delegado-especialidad con la especialidad explicita).

ALCANCE DE LA RECARGA (decision de negocio confirmada):
  - Borra TODOS los `DetalleHonorarioDelegado`, incluidos los detalles ligados
    a `ReciboHonorarioDelegadoMensual` (recibo_mensual no nulo).
  - Borra TODOS los `LiquidacionDelegado`.
  - NO borra `Delegado`, `DelegadoOperacion`, liquidaciones, inspectores ni
    ningun otro dato de dominio.
  - La unica fuente es el CSV: nunca se llama al endpoint CIP, nunca se crean
    placeholders de `PerfilIngeniero` y nunca se crean ni se habilitan
    operaciones de delegado como efecto secundario.

REGLAS DE ASOCIACION (una fila del CSV solo se asocia si cumple todas):
  1. NROORDEN debe ser mayor que cero, y MES y PERIODO deben ser validos.
     Si falta cualquiera de esos datos, la fila se omite como invalida.
  2. NRO -> `LiquidacionEdificacion.numero`. Si la liquidacion no existe en BD,
     la fila se omite (no se crea ninguna liquidacion).
  3. CIP -> `PerfilIngeniero.cip` normalizado (strip + zfill(6)) -> `Delegado`
     existente. Si el delegado no existe, la fila se omite.
   4. `DelegadoOperacion` es opcional: cuando hay una operacion habilitada se
      asocia como contexto; si no hay una compatible, queda NULL. Las
      operaciones ambiguas tampoco bloquean la importacion y quedan NULL.
   5. Especialidad: la `ESPECIALIDAD` del CSV (alias canonicos) es la fuente de
      la especialidad del RH. Cuando hay operacion, una diferencia se reporta
      pero la operacion nunca se modifica para forzar la coincidencia.
  6. Llave de identidad del CSV: (NRO, CIP, NROORDEN). Las repeticiones se
     omiten como duplicados.
  7. Restriccion de BD: `UniqueConstraint(liquidacion, delegado,
     especialidad_revision)`. Dos filas distintas con la misma terna entran en
     conflicto: se conserva la primera (orden del CSV) y se omite la otra.

MODO:
  - Sin `--apply` (default): DRY-RUN. Solo lee, planifica e informa.
  - Con `--apply --confirm-destructive`: borra e importa dentro de UNA sola
    transaccion (`transaction.atomic`). Cualquier error revierte todo el lote.

Uso:
    python manage.py import_rh_delegados_formal
    python manage.py import_rh_delegados_formal --apply --confirm-destructive
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
from django.db.models import Q
from django.utils import timezone

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado
from modules.liquidaciones.domain.constants import DictamenRevision
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision

# Reutilizacion del mapeo ya probado por la curacion existente.
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

# Sentinela historica: el curado la descarta como "sin dato".
SENTINEL_DATE = date(1900, 1, 1)

# ── Motivos de omision (contrato de reporte) ───────────────────────────────────
SKIP_INVALID_ROW = "fila_invalida"
SKIP_NO_LIQUIDACION = "sin_liquidacion_nro"
SKIP_NO_DELEGADO = "sin_delegado_cip"
SKIP_NO_OPERACION = "sin_operacion_habilitada"
SKIP_OPERACION_AMBIGUA = "operacion_ambigua"
SKIP_ESPECIALIDAD_DESCONOCIDA = "especialidad_desconocida"
SKIP_ESPECIALIDAD = "especialidad_no_coincide"
SKIP_DUPLICADO = "duplicado_csv"
SKIP_CONFLICTO = "conflicto_constraint"

SKIP_LABELS = {
    SKIP_INVALID_ROW: "Saltadas - fila invalida",
    SKIP_NO_LIQUIDACION: "Saltadas - sin liquidacion (NRO inexistente)",
    SKIP_NO_DELEGADO: "Saltadas - sin delegado (CIP inexistente)",
    SKIP_NO_OPERACION: "Saltadas - sin operacion habilitada",
    SKIP_OPERACION_AMBIGUA: "Saltadas - operacion ambigua",
    SKIP_ESPECIALIDAD_DESCONOCIDA: "Saltadas - especialidad inexistente en BD",
    SKIP_ESPECIALIDAD: "Saltadas - especialidad != operacion",
    SKIP_DUPLICADO: "Duplicados CSV",
    SKIP_CONFLICTO: "Conflictos de constraint (liquidacion+delegado+especialidad)",
}


# ── Helpers puros (testeables sin DB) ─────────────────────────────────────────


def strip_accents(value: str) -> str:
    """Quita acentos sin alterar el resto del texto."""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(value)) if unicodedata.category(c) != "Mn"
    )


def normalize_cip(raw) -> str:
    """CIP del CSV -> CIP normalizado (solo digitos, zfill(6))."""
    digits = "".join(c for c in str(raw or "").strip() if c.isdigit())
    return digits.zfill(6) if digits else ""


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


def resolve_operacion(candidates, tipo_liquidacion_id):
    """Elige la `DelegadoOperacion` habilitada para un delegado/municipalidad.

    Devuelve el dict de la operacion elegida, `{"estado": "ambigua"}` si hay
    mas de una candidata valida, o None si no hay ninguna.

    Reglas (mismo criterio que `resolve_delegado_operacion` del core service):
      - coincidencia exacta de `tipo_liquidacion` tiene prioridad;
      - una operacion con `tipo_liquidacion` NULL acts como wildcard;
      - exacta + wildcard a la vez, o varias wildcard, es ambigüedad.
    """
    exact = [
        op
        for op in candidates
        if op["tipo_liquidacion_id"] is not None
        and op["tipo_liquidacion_id"] == tipo_liquidacion_id
    ]
    wildcard = [op for op in candidates if op["tipo_liquidacion_id"] is None]
    if exact and wildcard:
        return {"estado": "ambigua"}
    if len(exact) == 1:
        return exact[0]
    if not exact and len(wildcard) == 1:
        return wildcard[0]
    if not exact and len(wildcard) > 1:
        return {"estado": "ambigua"}
    return None


# ── Modelo de datos del proceso ────────────────────────────────────────────────


@dataclass
class RhRow:
    """Fila del CSV normalizada y lista para asociar."""

    linea: int
    nro: int
    cip: str
    nro_orden: str
    especialidad_nombre: str
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
    """Fila asociada: liquidacion + delegado + especialidad y operacion opcional."""

    row: RhRow
    liquidacion_id: object
    delegado_id: object
    operacion_id: object | None
    especialidad_id: object
    especialidad_distinta: bool = False


@dataclass
class ImportReport:
    """Contadores del proceso (contrato de salida del comando)."""

    filas_leidas: int = 0
    filas_invalidas: int = 0
    importadas: int = 0
    importadas_con_importe_cero: int = 0
    importadas_con_especialidad_distinta: int = 0
    omitidas: dict = field(default_factory=lambda: defaultdict(int))
    eliminados_detalles: int = 0
    eliminados_delegados_rh: int = 0
    eliminados_recibos_honorario: int = 0

    @property
    def duplicados_conflictos(self) -> int:
        return self.omitidas[SKIP_DUPLICADO] + self.omitidas[SKIP_CONFLICTO]


def normalize_row(raw: dict, linea: int):
    """Fila cruda del CSV -> (RhRow | None, motivo_de_invalidez)."""
    nro = parse_int(raw.get("NRO"))
    if nro is None:
        return None, "nro_invalido"

    cip = normalize_cip(raw.get("CIP"))
    if not cip:
        return None, "cip_invalido"

    nro_orden = normalize_nro_rh(raw.get("NROORDEN"))
    if not nro_orden or int(nro_orden) == 0:
        return None, "nro_orden_invalido"

    especialidad = canonical_especialidad(raw.get("ESPECIALIDAD"))
    if not especialidad:
        return None, "especialidad_invalida"

    mes_raw = normalize_mes(raw.get("MES"))
    mes = int(mes_raw) if mes_raw and mes_raw.isdigit() and 1 <= int(mes_raw) <= 12 else None
    if mes is None:
        return None, "mes_invalido"

    periodo_raw = normalize_periodo(raw.get("PERIODO"))
    periodo = int(periodo_raw) if periodo_raw and len(periodo_raw) == 4 else None
    if periodo is None:
        return None, "periodo_invalido"

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
        "Recarga formal de RH Delegados desde RH_EDIF.csv. "
        "DRY-RUN por defecto; --apply --confirm-destructive borra e importa."
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
            help="Ejecutar el borrado y la importacion (default: dry-run).",
        )
        parser.add_argument(
            "--confirm-destructive",
            action="store_true",
            help=(
                "Confirmacion explicita del borrado. Sin este flag, --apply aborta. "
                "Reconoce que se borran TODOS los DetalleHonorarioDelegado y TODOS "
                "los LiquidacionDelegado."
            ),
        )
        parser.add_argument(
            "--allow-delete-recibos-honorario",
            action="store_true",
            help=(
                "Permite borrar tambien los ReciboHonorarioDelegado que protegen a "
                "los LiquidacionDelegado (FK PROTECT). Sin este flag el comando "
                "aborta si existen esos recibos."
            ),
        )
        parser.add_argument(
            "--allow-especialidad-mismatch",
            action="store_true",
            help=(
                "Permite asociar filas cuya ESPECIALIDAD del CSV difiere de la "
                "especialidad de la operacion habilitada (reportado aparte)."
            ),
        )
        parser.add_argument(
            "--vigencia-fecha",
            type=str,
            default=None,
            help=(
                "Fecha de referencia (YYYY-MM-DD) para determinar que "
                "DelegadoOperacion esta habilitada (default: hoy)."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Procesa solo las primeras N filas validas del CSV (smoke test).",
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
                "--apply requiere --confirm-destructive: la operacion borra TODOS los "
                "DetalleHonorarioDelegado y TODOS los LiquidacionDelegado."
            )
        if not rh_path.exists():
            raise CommandError(f"No existe el CSV de RH: {rh_path}")

        referencia = self._resolver_fecha(options.get("vigencia_fecha"))
        report = ImportReport()

        self.stdout.write(self.style.NOTICE("=" * 74))
        self.stdout.write(
            self.style.NOTICE(
                "import_rh_delegados_formal — "
                + ("APPLY (destructivo)" if apply else "DRY-RUN (sin escrituras)")
            )
        )
        self.stdout.write(self.style.NOTICE("=" * 74))
        self.stdout.write(f"  CSV:               {rh_path}")
        self.stdout.write(f"  Fecha de vigencia: {referencia.isoformat()}")
        self.stdout.write("")

        # Pre-flight: `ReciboHonorarioDelegado` protege a `LiquidacionDelegado`.
        recibos = ReciboHonorarioDelegado.objects.count()

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
        indexes = self._cargar_indexes(filas, referencia)
        especialidad_ids = build_especialidad_index(EspecialidadRevision.objects.all())
        self.stdout.write(f"  Liquidaciones (NRO):     {len(indexes['liquidaciones'])}")
        self.stdout.write(f"  Delegados (CIP):         {len(indexes['delegados'])}")
        self.stdout.write(f"  Operaciones habilitadas: {len(indexes['operaciones'])}")
        self.stdout.write(f"  Especialidades:          {len(especialidad_ids)}")
        self.stdout.write("")

        # ── 3. Planificacion ──────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("[3/5] Planificando..."))
        plan, omitidas, detalle_omitidas = self._planificar(
            filas,
            indexes,
            especialidad_ids,
            allow_especialidad_mismatch=bool(options["allow_especialidad_mismatch"]),
        )
        for motivo, cantidad in omitidas.items():
            report.omitidas[motivo] = cantidad
        report.importadas = len(plan)
        report.importadas_con_importe_cero = sum(
            1 for entry in plan if not entry.row.imp_bruto and not entry.row.neto_honorario
        )
        report.importadas_con_especialidad_distinta = sum(
            1 for entry in plan if entry.especialidad_distinta
        )
        self.stdout.write(f"  Filas a asociar:    {len(plan)}")
        self.stdout.write("")

        # ── 4. Borrado + importacion (una sola transaccion) ───────────────────
        self.stdout.write(self.style.HTTP_INFO("[4/5] Borrado + importacion..."))
        detalles = DetalleHonorarioDelegado.objects.count()
        delegados_rh = LiquidacionDelegado.objects.count()

        if recibos and not options["allow_delete_recibos_honorario"]:
            self.stdout.write(
                self.style.WARNING(
                    f"  [BLOQUEO] Hay {recibos} ReciboHonorarioDelegado que protegen a "
                    "los LiquidacionDelegado (on_delete=PROTECT). El --apply abortara "
                    "salvo que se use --allow-delete-recibos-honorario."
                )
            )

        if not apply:
            self.stdout.write(self.style.WARNING("  [DRY-RUN] No se ejecuta ninguna escritura."))
            self.stdout.write(f"  [DRY-RUN] DetalleHonorarioDelegado a borrar: {detalles}")
            self.stdout.write(f"  [DRY-RUN] LiquidacionDelegado a borrar:      {delegados_rh}")
            self.stdout.write(f"  [DRY-RUN] ReciboHonorarioDelegado a borrar:  {recibos}")
        else:
            if recibos and not options["allow_delete_recibos_honorario"]:
                raise CommandError(
                    f"Hay {recibos} ReciboHonorarioDelegado que protegen a los "
                    "LiquidacionDelegado (on_delete=PROTECT). No se puede borrar TODOS "
                    "los LiquidacionDelegado sin borrarlos. Revisa el dry-run y, si "
                    "corresponde, reintenta con --allow-delete-recibos-honorario."
                )
            with transaction.atomic():
                report.eliminados_detalles = self._borrar(DetalleHonorarioDelegado)
                if recibos:
                    report.eliminados_recibos_honorario = self._borrar(ReciboHonorarioDelegado)
                report.eliminados_delegados_rh = self._borrar(LiquidacionDelegado)
                self._importar(plan)
            self.stdout.write(self.style.SUCCESS("  Transaccion confirmada."))

        # ── 5. Reporte ────────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("[5/5] Reporte..."))
        self._imprimir_resumen(report)
        self._escribir_reporte(detalle_omitidas, invalidas, options)

        if apply:
            self.stdout.write(self.style.SUCCESS("Recarga formal de RH Delegados completada."))
        else:
            self.stdout.write(self.style.WARNING("DRY-RUN — no se modifico la base de datos."))

    # ── Paso 2: contexto de BD ───────────────────────────────────────────────

    def _cargar_indexes(self, filas, referencia: date) -> dict:
        """Carga en memoria los indices necesarios para resolver cada fila."""
        liquidaciones = {}
        if filas:
            numeros = [f.nro for f in filas]
            queryset = LiquidacionEdificacion.objects.filter(
                numero__gte=min(numeros), numero__lte=max(numeros)
            ).values(
                "numero",
                "liquidacion_id",
                "liquidacion__municipalidad_id",
                "liquidacion__tipo_liquidacion_id",
            )
            for item in queryset:
                liquidaciones[item["numero"]] = {
                    "liquidacion_id": item["liquidacion_id"],
                    "municipalidad_id": item["liquidacion__municipalidad_id"],
                    "tipo_liquidacion_id": item["liquidacion__tipo_liquidacion_id"],
                }

        delegados = {}
        for item in Delegado.objects.values("id", "perfil_ingeniero__cip"):
            cip = normalize_cip(item["perfil_ingeniero__cip"])
            if cip:
                delegados[cip] = item["id"]

        operaciones = defaultdict(list)
        habilitadas = DelegadoOperacion.objects.filter(
            Q(periodos__periodo_inicio__lte=referencia, periodos__periodo_fin__isnull=True)
            | Q(periodos__periodo_inicio__lte=referencia, periodos__periodo_fin__gte=referencia)
        ).values(
            "id",
            "delegado_id",
            "municipalidad_id",
            "tipo_liquidacion_id",
            "especialidad_revision_id",
        ).distinct()
        for operacion in habilitadas:
            operaciones[(operacion["delegado_id"], operacion["municipalidad_id"])].append(
                operacion
            )

        return {
            "liquidaciones": liquidaciones,
            "delegados": delegados,
            "operaciones": operaciones,
        }

    # ── Paso 3: planificacion ────────────────────────────────────────────────

    def _planificar(self, filas, indexes, especialidad_ids, allow_especialidad_mismatch: bool):
        """Resuelve cada fila: plan de importacion + detalle de omisiones."""
        plan: list[PlanEntry] = []
        omitidas: dict = defaultdict(int)
        detalle_omitidas: list[dict] = []

        vistos_csv = set()
        vistos_constraint = set()

        for fila in filas:
            motivo = None
            liquidacion = None
            delegado_id = None
            operacion = None
            especialidad_id = None

            if fila.key_csv in vistos_csv:
                motivo = SKIP_DUPLICADO
            else:
                vistos_csv.add(fila.key_csv)
                liquidacion = indexes["liquidaciones"].get(fila.nro)
                if liquidacion is None:
                    motivo = SKIP_NO_LIQUIDACION
                else:
                    delegado_id = indexes["delegados"].get(fila.cip)
                    if delegado_id is None:
                        motivo = SKIP_NO_DELEGADO
                    else:
                        especialidad_id = resolve_especialidad_id(
                            fila.especialidad_nombre, especialidad_ids
                        )
                        if especialidad_id is None:
                            motivo = SKIP_ESPECIALIDAD_DESCONOCIDA
                        else:
                            candidatas = indexes["operaciones"].get(
                                (delegado_id, liquidacion["municipalidad_id"]), ()
                            )
                            operacion = resolve_operacion(
                                candidatas, liquidacion["tipo_liquidacion_id"]
                            )
                            if operacion is not None and operacion.get("estado") == "ambigua":
                                operacion = None
                            elif (
                                operacion is not None
                                and especialidad_id != operacion["especialidad_revision_id"]
                                and not allow_especialidad_mismatch
                            ):
                                operacion = None

            if motivo is None:
                key_constraint = (
                    liquidacion["liquidacion_id"],
                    delegado_id,
                    especialidad_id,
                )
                if key_constraint in vistos_constraint:
                    motivo = SKIP_CONFLICTO
                else:
                    vistos_constraint.add(key_constraint)
                    plan.append(
                        PlanEntry(
                            row=fila,
                            liquidacion_id=liquidacion["liquidacion_id"],
                            delegado_id=delegado_id,
                            operacion_id=operacion["id"] if operacion is not None else None,
                            especialidad_id=especialidad_id,
                            especialidad_distinta=especialidad_id
                            != operacion["especialidad_revision_id"] if operacion is not None else False,
                        )
                    )

            if motivo is not None:
                omitidas[motivo] += 1
                detalle_omitidas.append(
                    {
                        "linea": fila.linea,
                        "nro": fila.nro,
                        "cip": fila.cip,
                        "nro_orden": fila.nro_orden,
                        "especialidad": fila.especialidad_nombre,
                        "motivo": motivo,
                    }
                )

        return plan, omitidas, detalle_omitidas

    # ── Paso 4: escritura ────────────────────────────────────────────────────

    def _borrar(self, model) -> int:
        """Borra todas las filas del modelo y devuelve el conteo eliminado."""
        total, _ = model.objects.all().delete()
        return total

    def _importar(self, plan) -> None:
        """Crea los LiquidacionDelegado y sus DetalleHonorarioDelegado."""
        for inicio in range(0, len(plan), BATCH_SIZE):
            lote = plan[inicio:inicio + BATCH_SIZE]
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

            creadas = LiquidacionDelegado.objects.bulk_create(
                asignaciones, batch_size=BATCH_SIZE
            )
            if any(asignacion.id is None for asignacion in creadas):
                creadas = self._recuperar_ids(lote)

            detalles = []
            for asignacion, entry in zip(creadas, lote):
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

    def _recuperar_ids(self, lote):
        """Resuelve los ids creados cuando el backend no devolvio las PK.

        La terna (liquidacion, delegado, especialidad_revision) es unica en BD
        (`UniqueConstraint`), por lo que la resolucion es 1:1.
        """
        liquidaciones = {entry.liquidacion_id for entry in lote}
        encontrados = {}
        for asignacion in LiquidacionDelegado.objects.filter(
            liquidacion_id__in=liquidaciones
        ).values("id", "liquidacion_id", "delegado_id", "especialidad_revision_id"):
            encontrados[
                (
                    asignacion["liquidacion_id"],
                    asignacion["delegado_id"],
                    asignacion["especialidad_revision_id"],
                )
            ] = asignacion["id"]

        resueltos = []
        for entry in lote:
            clave = (
                entry.liquidacion_id,
                entry.delegado_id,
                entry.especialidad_id,
            )
            if clave not in encontrados:
                raise CommandError(
                    "No se pudo resolver el id de la asignacion creada "
                    f"(liquidacion={entry.liquidacion_id}, delegado={entry.delegado_id})."
                )
            resueltos.append(
                LiquidacionDelegado(id=encontrados[clave], liquidacion_id=entry.liquidacion_id)
            )
        return resueltos

    # ── Reportes ─────────────────────────────────────────────────────────────

    def _imprimir_resumen(self, report: ImportReport) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("-" * 74))
        self.stdout.write(self.style.NOTICE("RESUMEN"))
        self.stdout.write(self.style.NOTICE("-" * 74))
        self.stdout.write(f"  Filas leidas (CSV):                {report.filas_leidas}")
        self.stdout.write(f"  Importadas (LiquidacionDelegado):  {report.importadas}")
        self.stdout.write(f"  Importadas (DetalleHonorario):     {report.importadas}")
        self.stdout.write(f"    - con importe cero:              {report.importadas_con_importe_cero}")
        if report.importadas_con_especialidad_distinta:
            self.stdout.write(
                f"    - con especialidad != operacion: {report.importadas_con_especialidad_distinta}"
            )
        self.stdout.write(
            f"  Saltadas - filas invalidas:         {report.filas_invalidas}"
        )
        for motivo in (
            SKIP_NO_LIQUIDACION,
            SKIP_NO_DELEGADO,
            SKIP_NO_OPERACION,
            SKIP_OPERACION_AMBIGUA,
            SKIP_ESPECIALIDAD_DESCONOCIDA,
            SKIP_ESPECIALIDAD,
        ):
            self.stdout.write(f"  {SKIP_LABELS[motivo]}: {report.omitidas[motivo]}")
        self.stdout.write(f"  Duplicados/conflictos:             {report.duplicados_conflictos}")
        self.stdout.write(f"    - Duplicados CSV:                {report.omitidas[SKIP_DUPLICADO]}")
        self.stdout.write(f"    - Conflictos de constraint:      {report.omitidas[SKIP_CONFLICTO]}")
        self.stdout.write("")
        self.stdout.write(f"  DetalleHonorarioDelegado borrados: {report.eliminados_detalles}")
        self.stdout.write(f"  LiquidacionDelegado borrados:      {report.eliminados_delegados_rh}")
        if report.eliminados_recibos_honorario:
            self.stdout.write(
                f"  ReciboHonorarioDelegado borrados:  {report.eliminados_recibos_honorario}"
            )
        self.stdout.write(
            "  Nota: las filas creadas con bulk_create no generan registro en "
            "simple_history (el borrado si queda auditado)."
        )
        self.stdout.write(self.style.NOTICE("-" * 74))

    def _escribir_reporte(self, omitidas_detalle, invalidas, options) -> None:
        out_path = options.get("output")
        if not out_path:
            ts = timezone.localtime().strftime("%Y%m%d_%H%M%S")
            modo = "apply" if options.get("apply") else "dryrun"
            out_path = DEFAULT_REPORT_DIR / f"import_rh_delegados_formal_{modo}_{ts}.csv"
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        header = ["linea", "nro", "cip", "nro_orden", "especialidad", "motivo"]
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
                        fila.get("motivo", ""),
                    ]
                )
        self.stdout.write(f"  Reporte de omitidas: {out_path}")

    # ── Utilidades ───────────────────────────────────────────────────────────

    def _resolver_fecha(self, raw) -> date:
        """Fecha de referencia para la vigencia de las operaciones."""
        if not raw:
            return timezone.localdate()
        try:
            return date.fromisoformat(str(raw).strip())
        except ValueError as exc:
            raise CommandError(f"--vigencia-fecha invalido: {raw} (se espera YYYY-MM-DD)") from exc
