import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.delegado import Delegado
from modules.liquidaciones.domain.models.inspector import Inspector
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero


class Command(BaseCleanSeedCommand):
    help = "Seed delegados + inspectores from clean JSON"
    SEED_PHASE = "personas_operativas"
    MODELS_TO_SEED = [Delegado, Inspector]
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
        self._seed_delegado(ctx, dry_run, verbose)
        self._seed_inspector(ctx, dry_run, verbose)

    def _seed_delegado(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_delegado.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "Delegado", len(rows), 0, 0, 0, 0.0
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
                if row.get("perfil_ingeniero_uuid"):
                    defaults["perfil_ingeniero"] = ctx.resolve_fk(
                        PerfilIngeniero, row["perfil_ingeniero_uuid"]
                    )
                if row.get("municipalidad_uuid"):
                    defaults["municipalidad"] = ctx.resolve_fk(
                        Municipalidad, row["municipalidad_uuid"]
                    )
                if row.get("tipo_liquidacion_uuid"):
                    defaults["tipo_liquidacion"] = ctx.resolve_fk(
                        TipoLiquidacion, row["tipo_liquidacion_uuid"]
                    )

                obj, was_created = Delegado.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(Delegado, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] Delegado {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR Delegado {row['uuid']}: {e}")

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "Delegado",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_inspector(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_inspector.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "Inspector", len(rows), 0, 0, 0, 0.0
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
                if row.get("perfil_ingeniero_uuid"):
                    defaults["perfil_ingeniero"] = ctx.resolve_fk(
                        PerfilIngeniero, row["perfil_ingeniero_uuid"]
                    )
                if row.get("municipalidad_uuid"):
                    defaults["municipalidad"] = ctx.resolve_fk(
                        Municipalidad, row["municipalidad_uuid"]
                    )
                if row.get("tipo_liquidacion_uuid"):
                    defaults["tipo_liquidacion"] = ctx.resolve_fk(
                        TipoLiquidacion, row["tipo_liquidacion_uuid"]
                    )

                obj, was_created = Inspector.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(Inspector, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] Inspector {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR Inspector {row['uuid']}: {e}")

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "Inspector",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )