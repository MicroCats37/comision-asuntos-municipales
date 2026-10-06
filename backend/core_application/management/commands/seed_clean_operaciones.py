import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.entidades.domain.models.entidad import Entidad
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
)
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorOperacion,
    InspectorOperacionPeriodo,
)


class Command(BaseCleanSeedCommand):
    help = "Seed operaciones (delegado + inspector) from clean JSON"
    SEED_PHASE = "operaciones"
    MODELS_TO_SEED = [
        DelegadoOperacion,
        DelegadoOperacionPeriodo,
        InspectorOperacion,
        InspectorOperacionPeriodo,
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
        self._seed_delegado_operacion(ctx, dry_run, verbose)
        self._seed_delegado_operacion_periodo(ctx, dry_run, verbose)
        self._seed_inspector_operacion(ctx, dry_run, verbose)
        self._seed_inspector_operacion_periodo(ctx, dry_run, verbose)

    def _process(
        self,
        model_cls,
        json_name,
        label,
        ctx,
        dry_run,
        verbose,
        fk_resolver=None,
    ):
        rows = self._load_json(json_name)
        if dry_run:
            self.print_summary(self.SEED_PHASE, label, len(rows), 0, 0, 0, 0.0)
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
                if fk_resolver:
                    fk_resolver(defaults, row, ctx)
                obj, was_created = model_cls.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(model_cls, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] {label} {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR {label} {row['uuid']}: {e}")

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE, label, len(rows), created, updated, errors, duration
        )

    def _seed_delegado_operacion(self, ctx, dry_run, verbose):
        def resolver(defaults, row, ctx):
            if row.get("delegado_uuid"):
                defaults["delegado"] = ctx.resolve_fk(Delegado, row["delegado_uuid"])
            if row.get("entidad_uuid"):
                defaults["entidad"] = ctx.resolve_fk(Entidad, row["entidad_uuid"])

        self._process(
            DelegadoOperacion,
            "liquidaciones_delegadooperacion.json",
            "DelegadoOperacion",
            ctx,
            dry_run,
            verbose,
            resolver,
        )

    def _seed_delegado_operacion_periodo(self, ctx, dry_run, verbose):
        def resolver(defaults, row, ctx):
            if row.get("delegado_operacion_uuid"):
                defaults["delegado_operacion"] = ctx.resolve_fk(
                    DelegadoOperacion, row["delegado_operacion_uuid"]
                )

        self._process(
            DelegadoOperacionPeriodo,
            "liquidaciones_delegadooperacionperiodo.json",
            "DelegadoOperacionPeriodo",
            ctx,
            dry_run,
            verbose,
            resolver,
        )

    def _seed_inspector_operacion(self, ctx, dry_run, verbose):
        def resolver(defaults, row, ctx):
            if row.get("inspector_uuid"):
                defaults["inspector"] = ctx.resolve_fk(
                    Inspector, row["inspector_uuid"]
                )
            if row.get("entidad_uuid"):
                defaults["entidad"] = ctx.resolve_fk(Entidad, row["entidad_uuid"])

        self._process(
            InspectorOperacion,
            "liquidaciones_inspectoroperacion.json",
            "InspectorOperacion",
            ctx,
            dry_run,
            verbose,
            resolver,
        )

    def _seed_inspector_operacion_periodo(self, ctx, dry_run, verbose):
        def resolver(defaults, row, ctx):
            if row.get("inspector_operacion_uuid"):
                defaults["inspector_operacion"] = ctx.resolve_fk(
                    InspectorOperacion, row["inspector_operacion_uuid"]
                )

        self._process(
            InspectorOperacionPeriodo,
            "liquidaciones_inspectoroperacionperiodo.json",
            "InspectorOperacionPeriodo",
            ctx,
            dry_run,
            verbose,
            resolver,
        )