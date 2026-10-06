import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type

from django.core.management.base import BaseCommand
from django.db.models import Model


@dataclass
class SeedContext:
    cache: Dict[Tuple[str, str], Model] = field(default_factory=dict)

    def make_key(self, model_cls, uuid_str):
        return (model_cls.__name__, str(uuid_str))

    def store(self, model_cls, uuid_str, instance):
        self.cache[self.make_key(model_cls, uuid_str)] = instance

    def get(self, model_cls, uuid_str):
        return self.cache.get(self.make_key(model_cls, uuid_str))

    def resolve_fk(self, model_cls, uuid_str):
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
    MODELS_TO_SEED: List = []

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
        from django.test.utils import override_settings

        saved_flags = []
        for model_cls in self.MODELS_TO_SEED:
            if issubclass(model_cls, AutoNumeroModel):
                was_set = getattr(model_cls, "_skip_autonumero_seed", False)
                saved_flags.append((model_cls, was_set))
                model_cls._skip_autonumero_seed = True

        with override_settings(SIMPLE_HISTORY_ENABLED=False):
            try:
                yield
            finally:
                for model_cls, was_set in saved_flags:
                    if was_set:
                        model_cls._skip_autonumero_seed = True
                    else:
                        if hasattr(model_cls, "_skip_autonumero_seed"):
                            delattr(model_cls, "_skip_autonumero_seed")

    def resolve_fk(self, context, model_cls, uuid_str):
        if not uuid_str:
            return None
        return context.resolve_fk(model_cls, uuid_str)

    def smart_update_or_create(
        self,
        model_cls,
        row,
        context,
        resolver=None,
        dry_run=False,
    ):
        """
        Smart upsert: SELECT existing row, compare fields, UPDATE only if different.

        If dry_run=True: validate fields and FK resolution, but don't write.

        Returns (obj, action) where action is:
        - 'created' / 'would_create'  → row did not exist (dry-run variant in parens)
        - 'updated' / 'would_update'  → row existed and at least one field changed
        - 'unchanged'                 → row existed and no field changed
        - 'invalid_field:<name>'      → JSON key is not a model field (caught early)
        """
        uuid_val = row.get("uuid")
        defaults = {
            k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
        }
        if resolver:
            resolver(defaults, row, context)

        valid_fields = {f.name for f in model_cls._meta.get_fields()}
        for field_name in defaults:
            if field_name not in valid_fields:
                return None, f"invalid_field:{field_name}"

        try:
            existing = model_cls.objects.get(id=uuid_val)
        except model_cls.DoesNotExist:
            if dry_run:
                return None, "would_create"
            obj = model_cls.objects.create(id=uuid_val, **defaults)
            context.store(model_cls, obj.id, obj)
            return obj, "created"

        changed = False
        for field, value in defaults.items():
            current_value = getattr(existing, field, None)
            if current_value != value:
                changed = True
                if not dry_run:
                    setattr(existing, field, value)
        if changed:
            if dry_run:
                return existing, "would_update"
            existing.save()
            context.store(model_cls, existing.id, existing)
            return existing, "updated"

        return existing, "unchanged"

    def apply_m2m(self, obj, field_name, uuids_list, context):
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
        self, phase_name, table_name, source_count, created_count, updated_count, error_count, duration
    ):
        print(
            f"[{phase_name}] {table_name}: "
            f"total={source_count} created={created_count} "
            f"updated={updated_count} errors={error_count} "
            f"duration={duration:.2f}s"
        )

    def _progress(self, label, current, total, start_time, extra=""):
        if total == 0:
            return
        pct = int(current * 100 / total)
        elapsed = time.time() - start_time
        rate = current / elapsed if elapsed > 0 else 0
        eta_s = (total - current) / rate if rate > 0 else 0
        bar_len = 30
        filled = int(bar_len * current / total)
        if filled >= bar_len:
            filled = bar_len - 1
        bar = "=" * filled + ">" + " " * (bar_len - filled - 1)
        extra_str = f" {extra}" if extra else ""
        self.stdout.write(
            f"\r  [{bar}] {pct:3d}% {current}/{total} {label}{extra_str} "
            f"[{elapsed:.0f}s, ETA {eta_s:.0f}s]   ",
            ending="",
        )
        self.stdout.flush()
        if current >= total:
            self.stdout.write("")

    def _bulk_smart(
        self,
        model_cls,
        rows,
        ctx,
        resolver=None,
        verbose=False,
        progress=True,
        dry_run=False,
    ):
        total = len(rows)
        created = updated = unchanged = errors = 0
        start = time.time()
        last_report = start
        for i, row in enumerate(rows, 1):
            try:
                obj, action = self.smart_update_or_create(
                    model_cls, row, ctx, resolver=resolver, dry_run=dry_run
                )
                if action in ("created", "would_create"):
                    created += 1
                elif action in ("updated", "would_update"):
                    updated += 1
                elif action == "unchanged":
                    unchanged += 1
                else:
                    errors += 1
                    self.stdout.write(
                        f"\nERROR {model_cls.__name__} {row.get('uuid', '')}: {action}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"\nERROR {model_cls.__name__} {row.get('uuid', '')}: {e}"
                )
            if progress and total >= 50:
                now = time.time()
                if now - last_report >= 2 or i == total:
                    self._progress(
                        model_cls.__name__,
                        i,
                        total,
                        start,
                        extra=f"new={created} upd={updated} same={unchanged}",
                    )
                    last_report = now
        return created, updated, unchanged, errors


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