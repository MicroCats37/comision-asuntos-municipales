import json
import time
from pathlib import Path

from django.contrib.auth import get_user_model

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.entidades.domain.models.contacto import Contacto
from modules.entidades.domain.models.entidad import Entidad
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


class Command(BaseCleanSeedCommand):
    help = "Seed LiquidacionGeneral from clean JSON"
    SEED_PHASE = "liquidacion_general"
    MODELS_TO_SEED = [LiquidacionGeneral]
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
        self._seed_liquidacion_general(ctx, dry_run, verbose)

    def _resolve_user(self, username):
        if not username:
            return None
        User = get_user_model()
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    def _seed_liquidacion_general(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidaciongeneral.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "LiquidacionGeneral", len(rows), 0, 0, 0, 0.0
            )
            return

        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v
                    for k, v in row.items()
                    if k not in (
                        "uuid",
                        "especialidades_revisadas_uuids",
                        "usuario_creador_username",
                    )
                    and not k.endswith("_uuid")
                }

                if row.get("proyecto_uuid"):
                    defaults["proyecto"] = ctx.resolve_fk(
                        Proyecto, row["proyecto_uuid"]
                    )
                if row.get("municipalidad_uuid"):
                    defaults["municipalidad"] = ctx.resolve_fk(
                        Municipalidad, row["municipalidad_uuid"]
                    )
                if row.get("igv_uuid"):
                    defaults["igv_id"] = ctx.resolve_fk(IGV, row["igv_uuid"])
                if row.get("uit_uuid"):
                    defaults["uit_id"] = ctx.resolve_fk(UIT, row["uit_uuid"])
                if row.get("tipo_liquidacion_uuid"):
                    defaults["tipo_liquidacion"] = ctx.resolve_fk(
                        TipoLiquidacion, row["tipo_liquidacion_uuid"]
                    )
                if row.get("contacto_uuid"):
                    defaults["contacto"] = ctx.resolve_fk(
                        Contacto, row["contacto_uuid"]
                    )
                if row.get("eliminado_por_uuid"):
                    User = get_user_model()
                    user = self._resolve_user_by_uuid(row["eliminado_por_uuid"])
                    defaults["eliminado_por"] = user

                if row.get("usuario_creador_username"):
                    defaults["usuario_creador"] = self._resolve_user(
                        row["usuario_creador_username"]
                    )

                obj, was_created = LiquidacionGeneral.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(LiquidacionGeneral, obj.id, obj)

                m2m_uuids = row.get("especialidades_revisadas_uuids") or []
                if m2m_uuids:
                    self.apply_m2m(
                        obj, "especialidades_revisadas", m2m_uuids, ctx
                    )

                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] LiquidacionGeneral {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR LiquidacionGeneral {row['uuid']}: {e}"
                )

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionGeneral",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _resolve_user_by_uuid(self, uuid_str):
        if not uuid_str:
            return None
        User = get_user_model()
        try:
            return User.objects.get(id=uuid_str)
        except User.DoesNotExist:
            return None