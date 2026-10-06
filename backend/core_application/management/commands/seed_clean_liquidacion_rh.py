import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.liquidaciones.domain.models.delegado import Delegado
from modules.liquidaciones.domain.models.delegado import DelegadoOperacion
from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado
from modules.liquidaciones.domain.models.inspector import Inspector
from modules.liquidaciones.domain.models.inspector import InspectorOperacion
from modules.liquidaciones.domain.models.inspector import LiquidacionInspector
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


class Command(BaseCleanSeedCommand):
    help = "Seed liquidaciones RH (inspector + delegado + detalle honorario + comprobante)"
    SEED_PHASE = "liquidacion_rh"
    MODELS_TO_SEED = [
        LiquidacionInspector,
        LiquidacionDelegado,
        DetalleHonorarioDelegado,
        LiquidacionComprobante,
    ]
    SEEDS_DIR = (
        Path(__file__).resolve().parent.parent.parent
        / "seeds"
        / "migrados"
    )

    def _load_json(self, filename):
        with open(self.SEEDS_DIR / filename, encoding="utf-8") as f:
            return json.load(f)

    def handle_phase(self, *args, **options):
        ctx = SeedContext()
        dry_run = options.get("dry_run", False)
        verbose = options.get("verbose", False)
        self._seed_inspector(ctx, dry_run, verbose)
        self._seed_delegado(ctx, dry_run, verbose)
        self._seed_detalle_honorario(ctx, dry_run, verbose)
        self._seed_comprobante(ctx, dry_run, verbose)

    def _seed_inspector(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidacioninspector.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE,
                "LiquidacionInspector",
                len(rows),
                0,
                0,
                0,
                0.0,
            )
            return

        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v
                    for k, v in row.items()
                    if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("liquidacion_uuid"):
                    defaults["liquidacion"] = ctx.resolve_fk(
                        LiquidacionGeneral, row["liquidacion_uuid"]
                    )
                if row.get("inspector_uuid"):
                    defaults["inspector"] = ctx.resolve_fk(
                        Inspector, row["inspector_uuid"]
                    )
                if row.get("inspector_operacion_uuid"):
                    defaults["inspector_operacion"] = ctx.resolve_fk(
                        InspectorOperacion, row["inspector_operacion_uuid"]
                    )
                if row.get("especialidad_revision_uuid"):
                    defaults["especialidad_revision"] = ctx.resolve_fk(
                        EspecialidadRevision, row["especialidad_revision_uuid"]
                    )

                obj, was_created = LiquidacionInspector.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] LiquidacionInspector {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR LiquidacionInspector {row['uuid']}: {e}"
                )

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionInspector",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_delegado(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidaciondelegado.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE,
                "LiquidacionDelegado",
                len(rows),
                0,
                0,
                0,
                0.0,
            )
            return

        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v
                    for k, v in row.items()
                    if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("liquidacion_uuid"):
                    defaults["liquidacion"] = ctx.resolve_fk(
                        LiquidacionGeneral, row["liquidacion_uuid"]
                    )
                if row.get("delegado_uuid"):
                    defaults["delegado"] = ctx.resolve_fk(
                        Delegado, row["delegado_uuid"]
                    )
                if row.get("delegado_operacion_uuid"):
                    defaults["delegado_operacion"] = ctx.resolve_fk(
                        DelegadoOperacion, row["delegado_operacion_uuid"]
                    )
                if row.get("especialidad_revision_uuid"):
                    defaults["especialidad_revision"] = ctx.resolve_fk(
                        EspecialidadRevision, row["especialidad_revision_uuid"]
                    )

                obj, was_created = LiquidacionDelegado.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(LiquidacionDelegado, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] LiquidacionDelegado {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR LiquidacionDelegado {row['uuid']}: {e}"
                )

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionDelegado",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_detalle_honorario(self, ctx, dry_run, verbose):
        rows = self._load_json("finanzas_detallehonorariodelegado.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE,
                "DetalleHonorarioDelegado",
                len(rows),
                0,
                0,
                0,
                0.0,
            )
            return

        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v
                    for k, v in row.items()
                    if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("liquidacion_delegado_uuid"):
                    defaults["liquidacion_delegado"] = ctx.resolve_fk(
                        LiquidacionDelegado, row["liquidacion_delegado_uuid"]
                    )

                obj, was_created = DetalleHonorarioDelegado.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] DetalleHonorarioDelegado {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR DetalleHonorarioDelegado {row['uuid']}: {e}"
                )

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "DetalleHonorarioDelegado",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_comprobante(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidacioncomprobante.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE,
                "LiquidacionComprobante",
                len(rows),
                0,
                0,
                0,
                0.0,
            )
            return

        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v
                    for k, v in row.items()
                    if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("liquidacion_general_uuid"):
                    defaults["liquidacion_general"] = ctx.resolve_fk(
                        LiquidacionGeneral, row["liquidacion_general_uuid"]
                    )

                obj, was_created = LiquidacionComprobante.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] LiquidacionComprobante {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR LiquidacionComprobante {row['uuid']}: {e}"
                )

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionComprobante",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )