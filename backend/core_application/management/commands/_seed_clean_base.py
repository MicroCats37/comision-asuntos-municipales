import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type

from django.core.management.base import BaseCommand
from django.db.models import Model


@dataclass
class SeedContext:
    cache: Dict[Tuple[str, str], Model] = field(default_factory=dict)

    def make_key(self, model_cls: Type[Model], uuid_str: str) -> Tuple[str, str]:
        return (model_cls.__name__, str(uuid_str))

    def store(self, model_cls: Type[Model], uuid_str: str, instance: Model) -> None:
        self.cache[self.make_key(model_cls, uuid_str)] = instance

    def get(self, model_cls: Type[Model], uuid_str: str) -> Optional[Model]:
        return self.cache.get(self.make_key(model_cls, uuid_str))

    def resolve_fk(
        self, model_cls: Type[Model], uuid_str: str
    ) -> Optional[Model]:
        if not uuid_str:
            return None
        cached = self.get(model_cls, uuid_str)
        if cached is not None:
            return cached
        try:
            instance = model_cls.objects.get(id=uuid_str)
            self.store(model_cls, uuid_str, instance)
            return instance
        except model_cls.DoesNotExist:
            return None


class BaseCleanSeedCommand(BaseCommand):
    SEED_PHASE: str = "unknown"
    MODELS_TO_SEED: List[Type[Model]] = []

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument("--only", type=str, default="")

    def handle(self, *args, **options):
        with self.seed_context():
            return self.handle_phase(*args, **options)

    @contextmanager
    def seed_context(self):
        from core_application.models import AutoNumeroModel

        saved_flags: List[Tuple[Type[Model], bool]] = []
        for model_cls in self.MODELS_TO_SEED:
            if issubclass(model_cls, AutoNumeroModel):
                was_set = getattr(model_cls, "_skip_autonumero_seed", False)
                saved_flags.append((model_cls, was_set))
                model_cls._skip_autonumero_seed = True
        try:
            yield
        finally:
            for model_cls, was_set in saved_flags:
                if was_set:
                    model_cls._skip_autonumero_seed = True
                else:
                    if hasattr(model_cls, "_skip_autonumero_seed"):
                        delattr(model_cls, "_skip_autonumero_seed")

    def resolve_fk(
        self, context: SeedContext, model_cls: Type[Model], uuid_str: str
    ) -> Optional[Model]:
        if not uuid_str:
            return None
        return context.resolve_fk(model_cls, uuid_str)

    def update_or_create_with_signals_off(
        self,
        model_cls: Type[Model],
        row: Dict[str, Any],
        context: SeedContext,
    ) -> Tuple[Model, bool]:
        from core_application.models import AutoNumeroModel

        uuid_val = row.get("uuid")
        defaults = {k: v for k, v in row.items() if k != "uuid"}

        if issubclass(model_cls, AutoNumeroModel) and "numero" in defaults:
            numero_val = defaults.pop("numero")
            obj, was_created = model_cls.objects.update_or_create(
                id=uuid_val, defaults=defaults
            )
            if numero_val is not None:
                obj.numero = numero_val
                obj.save()
        else:
            obj, was_created = model_cls.objects.update_or_create(
                id=uuid_val, defaults=defaults
            )

        return obj, was_created

    def apply_m2m(
        self,
        obj: Model,
        field_name: str,
        uuids_list: List[str],
        context: SeedContext,
    ) -> None:
        if not uuids_list:
            getattr(obj, field_name).set([])
            return
        m2m_field = getattr(obj.__class__, field_name)
        related_model = m2m_field.related_model
        resolved_instances = []
        for uuid_str in uuids_list:
            instance = context.resolve_fk(related_model, uuid_str)
            if instance is not None:
                resolved_instances.append(instance)
        getattr(obj, field_name).set(resolved_instances)

    def print_summary(
        self,
        phase_name: str,
        table_name: str,
        source_count: int,
        created_count: int,
        updated_count: int,
        error_count: int,
        duration: float,
    ) -> None:
        print(
            f"[{phase_name}] {table_name}: "
            f"total={source_count} created={created_count} "
            f"updated={updated_count} errors={error_count} "
            f"duration={duration:.2f}s"
        )


if __name__ == "__main__":
    ctx = SeedContext()
    assert ctx.cache == {}
    key = ctx.make_key("Usuario", "abc-123")
    assert key == ("Usuario", "abc-123")

    class FakeModel:
        class DoesNotExist(Exception):
            pass

    ctx.store(FakeModel, "uuid-1", "instance-1")
    assert ctx.get(FakeModel, "uuid-1") == "instance-1"
    assert ctx.get(FakeModel, "nonexistent") is None
    print("SeedContext smoke test: PASSED")