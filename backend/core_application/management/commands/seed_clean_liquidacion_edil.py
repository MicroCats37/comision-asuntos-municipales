import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    TarifaPorcentajeObra,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


class Command(BaseCleanSeedCommand):
    help = "Seed liquidaciones EDIL (edificacion, porcentajeobra, detalle) from clean JSON"
    SEED_PHASE = "liquidacion_edil"
    MODELS_TO_SEED = [
        LiquidacionEdificacion,
        LiquidacionPorcentajeObra,
        LiquidacionPorcentajeObraDetalle,
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
        self._seed_edificacion(ctx, dry_run, verbose)
        self._seed_porcentaje_obra(ctx, dry_run, verbose)
        self._seed_porcentaje_obra_detalle(ctx, dry_run, verbose)

    def _seed_edificacion(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidacionedificacion.json")
        start = time.time()
        created = updated = unchanged = errors = 0
        for row in rows:
            try:
                if row.get("liquidacion_uuid"):
                    ctx.resolve_fk(LiquidacionGeneral, row["liquidacion_uuid"])
                _, action = self.smart_update_or_create(
                    LiquidacionEdificacion, row, ctx, dry_run=dry_run
                )
                if action == "created" or action == "would_create":
                    created += 1
                elif action == "updated" or action == "would_update":
                    updated += 1
                elif action.startswith("invalid_field"):
                    errors += 1
                    self.stdout.write(f"\nERROR {row.get('uuid','')}: {action}")
                else:
                    unchanged += 1
            except Exception as e:
                errors += 1
                self.stdout.write(f"\nERROR {row.get('uuid','')}: {e}")
        duration = time.time() - start
        if dry_run:
            self.stdout.write(
                f"[DRY {self.SEED_PHASE}] LiquidacionEdificacion: "
                f"total={len(rows)} would_create={created} would_update={updated} unchanged={unchanged} errors={errors} duration={duration:.2f}s"
            )
        else:
            self.print_summary(
                self.SEED_PHASE,
                "LiquidacionEdificacion",
                len(rows),
                created,
                updated,
                errors,
                duration,
            )

    def _seed_porcentaje_obra(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidacionporcentajeobra.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE,
                "LiquidacionPorcentajeObra",
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
                if row.get("derecho_aplicado_uuid"):
                    defaults["derecho_aplicado"] = ctx.resolve_fk(
                        DerechoPorcentajeObra, row["derecho_aplicado_uuid"]
                    )

                obj, was_created = LiquidacionPorcentajeObra.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(LiquidacionPorcentajeObra, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] LiquidacionPorcentajeObra {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR LiquidacionPorcentajeObra {row['uuid']}: {e}"
                )

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionPorcentajeObra",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_porcentaje_obra_detalle(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidacionporcentajeobradetalle.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE,
                "LiquidacionPorcentajeObraDetalle",
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
                if row.get("liquidacion_porcentaje_uuid"):
                    defaults["liquidacion_porcentaje"] = ctx.resolve_fk(
                        LiquidacionPorcentajeObra, row["liquidacion_porcentaje_uuid"]
                    )
                if row.get("tarifa_aplicada_uuid"):
                    defaults["tarifa_aplicada"] = ctx.resolve_fk(
                        TarifaPorcentajeObra, row["tarifa_aplicada_uuid"]
                    )
                if row.get("especialidad_uuid"):
                    defaults["especialidad"] = ctx.resolve_fk(
                        EspecialidadRevision, row["especialidad_uuid"]
                    )

                obj, was_created = LiquidacionPorcentajeObraDetalle.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] LiquidacionPorcentajeObraDetalle {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR LiquidacionPorcentajeObraDetalle {row['uuid']}: {e}"
                )

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionPorcentajeObraDetalle",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )