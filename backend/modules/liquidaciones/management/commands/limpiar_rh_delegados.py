"""
limpiar_rh_delegados — Limpieza EXCLUSIVA de los registros de RH Delegados.

Comando DESTRUCTIVO de alcance cerrado: borra TODOS los registros de los cuatro
modelos del agregado de honorarios de delegado y NADA mas.

Modelos borrados (TODOS los registros, sin filtros):
    1. DetalleHonorarioDelegado
    2. ReciboHonorarioDelegado
    3. ReciboHonorarioDelegadoMensual
    4. LiquidacionDelegado

NO borra: `Delegado`, `DelegadoOperacion`, `DelegadoOperacionPeriodo`,
`PerfilIngeniero`, liquidaciones, proyectos, municipalidades, inspectores ni
ningun otro dato de dominio. Los catálogos de profesionales se conservan
integros porque son catalogo con historial.

Este comando NO importa datos: no lee ningun CSV, no llama al endpoint CIP y
no crea asignaciones. Su unico proposito es dejar la base sin el dataset de
RH Delegados (historico y emitido) previo a la recarga formal, que es una
operacion separada (`import_rh_delegados_formal`).

DECISION DE NEGOCIO (confirmada por el usuario): la eliminacion es
intencional incluso para los detalles ligados a RH mensuales ya emitidos
(`recibo_mensual` no nulo) y para los `ReciboHonorarioDelegado` /
`ReciboHonorarioDelegadoMensual` existentes.

MODO:
    - Default: DRY-RUN. Solo cuenta e informa. Cero escrituras.
    - `--apply --confirm-destructive`: borra dentro de UNA sola
      `transaction.atomic()`. Cualquier error revierte el lote completo.

Uso:
    python manage.py limpiar_rh_delegados
    python manage.py limpiar_rh_delegados --apply --confirm-destructive
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models.deletion import ProtectedError

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
)
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
    LiquidacionDelegado,
)


# Orden de borrado por dependencia (`on_delete=PROTECT`): de hijos a padres.
MODELOS_A_BORRAR = (
    ("DetalleHonorarioDelegado", DetalleHonorarioDelegado),
    ("ReciboHonorarioDelegado", ReciboHonorarioDelegado),
    ("ReciboHonorarioDelegadoMensual", ReciboHonorarioDelegadoMensual),
    ("LiquidacionDelegado", LiquidacionDelegado),
)

# Catalogo de profesionales: se verifica antes y despues, pero NO se toca.
MODELOS_A_PRESERVAR = (
    ("Delegado", Delegado),
    ("DelegadoOperacion", DelegadoOperacion),
    ("DelegadoOperacionPeriodo", DelegadoOperacionPeriodo),
)

# Lote de borrado: mantiene acotada la memoria y permite reportar progreso
# sin abrir multiples transacciones.
BATCH_SIZE = 5000


class Command(BaseCommand):
    help = (
        "Borra TODOS los DetalleHonorarioDelegado, ReciboHonorarioDelegado, "
        "ReciboHonorarioDelegadoMensual y LiquidacionDelegado. DRY-RUN por "
        "defecto; exige --apply --confirm-destructive para escribir. NO importa "
        "CSV ni toca delegados, operaciones ni liquidaciones."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Ejecuta el borrado dentro de UNA sola transaccion. Sin este flag "
                "el comando es DRY-RUN (solo lectura)."
            ),
        )
        parser.add_argument(
            "--confirm-destructive",
            action="store_true",
            help=(
                "Confirmacion explicita de la operacion destructiva. "
                "--apply sin este flag aborta con CommandError."
            ),
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _tablas_existentes(self) -> set:
        return set(connection.introspection.table_names())

    def _conteo(self, modelo, tablas_existentes) -> int:
        """Conteo de registros; devuelve 0 si la tabla no existe todavia."""
        if modelo._meta.db_table not in tablas_existentes:
            return 0
        return modelo.objects.count()

    def _borrar_en_lotes(self, modelo, nombre, tablas_existentes) -> int:
        """
        Borra TODOS los registros de `modelo` por lotes de `BATCH_SIZE`.

        Devuelve el numero de registros efectivamente borrados del modelo.
        """
        if modelo._meta.db_table not in tablas_existentes:
            self.stdout.write(self.style.WARNING(f"  {nombre}: tabla no existe, se omite"))
            return 0

        borrados_total = 0
        while True:
            ids = list(modelo.objects.values_list("id", flat=True)[:BATCH_SIZE])
            if not ids:
                break
            borrados, _ = modelo.objects.filter(id__in=ids).delete()
            borrados_total += len(ids)
            self.stdout.write(f"    {nombre}: {borrados_total} borrados (lote de {len(ids)})")
        return borrados_total

    # ── Command ────────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        apply = bool(options.get("apply"))
        confirm = bool(options.get("confirm_destructive"))

        if apply and not confirm:
            raise CommandError(
                "--apply requiere --confirm-destructive: la operacion borra TODOS "
                "los DetalleHonorarioDelegado, ReciboHonorarioDelegado, "
                "ReciboHonorarioDelegadoMensual y LiquidacionDelegado. Sin la "
                "confirmacion explicita no se ejecuta ninguna escritura."
            )

        db = settings.DATABASES["default"]
        self.stdout.write(f"Base de datos: {db['NAME']} @ {db['HOST']}:{db['PORT']}")
        self.stdout.write(f"Modo: {'APPLY (destructivo)' if apply else 'DRY-RUN (solo lectura)'}")

        tablas_existentes = self._tablas_existentes()

        # ── Conteo previo ──────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write("Conteo previo (registros a eliminar):")
        conteos_previas = {}
        for nombre, modelo in MODELOS_A_BORRAR:
            conteo = self._conteo(modelo, tablas_existentes)
            conteos_previas[nombre] = conteo
            self.stdout.write(f"  {nombre}: {conteo}")

        # Detalle del split historico vs emitido (ambos se borran).
        if DetalleHonorarioDelegado._meta.db_table in tablas_existentes:
            historicos = DetalleHonorarioDelegado.objects.filter(
                recibo_mensual__isnull=True
            ).count()
            emitidos = DetalleHonorarioDelegado.objects.filter(
                recibo_mensual__isnull=False
            ).count()
            self.stdout.write(
                f"    (detalle historico recibo_mensual NULL: {historicos} | "
                f"detalle de RH mensual emitido: {emitidos} | ambos se eliminan)"
            )

        preservados_previas = {}
        for nombre, modelo in MODELOS_A_PRESERVAR:
            conteo = self._conteo(modelo, tablas_existentes)
            preservados_previas[nombre] = conteo
        self.stdout.write("")
        self.stdout.write("Catalogo preservado (NO se borra):")
        for nombre, conteo in preservados_previas.items():
            self.stdout.write(f"  {nombre}: {conteo}")

        if not apply:
            total = sum(conteos_previas.values())
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    f"DRY-RUN — {total} registros a eliminar. No se realizo ninguna escritura."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "Para ejecutar el borrado: --apply --confirm-destructive"
                )
            )
            return

        # ── Borrado ────────────────────────────────────────────────────────────
        self.stdout.write("")
        try:
            with transaction.atomic():
                borrados_por_modelo = {}
                for nombre, modelo in MODELOS_A_BORRAR:
                    self.stdout.write(f"  Borrando {nombre}...")
                    borrados_por_modelo[nombre] = self._borrar_en_lotes(
                        modelo, nombre, tablas_existentes
                    )
        except ProtectedError as exc:
            raise CommandError(
                "Borrado abortado por una dependencia PROTECT no prevista: "
                f"{exc}. La transaccion fue revertida (no se borro nada). "
                "No se borra ningun modelo fuera del alcance de este comando."
            ) from exc

        # ── Conteo final ───────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write("Conteo final (registros eliminados):")
        for nombre, modelo in MODELOS_A_BORRAR:
            restantes = self._conteo(modelo, tablas_existentes)
            self.stdout.write(
                f"  {nombre}: {borrados_por_modelo[nombre]} borrados | "
                f"restantes: {restantes}"
            )

        total_borrado = sum(borrados_por_modelo.values())
        self.stdout.write("")
        self.stdout.write("Catalogo preservado (verificacion posterior):")
        for nombre, modelo in MODELOS_A_PRESERVAR:
            restantes = self._conteo(modelo, tablas_existentes)
            estado = "OK" if restantes == preservados_previas[nombre] else "CAMBIADO"
            self.stdout.write(
                f"  {nombre}: {restantes} (antes: {preservados_previas[nombre]}) [{estado}]"
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Limpieza completada en una sola transaccion. {total_borrado} registros eliminados."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Delegados, operaciones de delegacion, liquidaciones, proyectos y "
                "municipalidades NO fueron tocados."
            )
        )
