import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)


class Command(BaseCleanSeedCommand):
    help = "Seed liquidaciones IO (inspeccion obra, por categoria visitas) from clean JSON"
    SEED_PHASE = "liquidacion_io"
    MODELS_TO_SEED = [
        LiquidacionInspeccionObra,
        LiquidacionPorCategoriaVisitas,
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
        self._seed_io(ctx, dry_run, verbose)
        self._seed_pcv(ctx, dry_run, verbose)

    def _seed_io(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidacioninspeccionobra.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE,
                "LiquidacionInspeccionObra",
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

                obj, was_created = LiquidacionInspeccionObra.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] LiquidacionInspeccionObra {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR LiquidacionInspeccionObra {row['uuid']}: {e}"
                )

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionInspeccionObra",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_pcv(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidacionporcategoriavisitas.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE,
                "LiquidacionPorCategoriaVisitas",
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

                obj, was_created = LiquidacionPorCategoriaVisitas.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(LiquidacionPorCategoriaVisitas, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] LiquidacionPorCategoriaVisitas {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR LiquidacionPorCategoriaVisitas {row['uuid']}: {e}"
                )

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionPorCategoriaVisitas",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )