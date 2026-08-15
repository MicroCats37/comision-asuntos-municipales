# Generated manually — Fase 1: Remove especialidad FK from TarifaPorcentajeObra

import uuid
from django.db import migrations, models


def consolidate_tarifa_porcentaje_obra(apps, schema_editor):
    """
    Consolidate existing TarifaPorcentajeObra records:
    - For each tarifa_base, keep ONE record (the one with highest porcentaje_liquidacion).
    - Delete all others (they become redundant after especialidad FK removal).
    - User confirmed old values ~0.05, new system uses explicit especialidad from
      LiquidacionEspecialidadDisponibles per entry.
    """
    db_alias = schema_editor.connection.alias
    TarifaPorcentajeObra = apps.get_model('liquidaciones', 'TarifaPorcentajeObra')

    # Group by tarifa_base
    from collections import defaultdict
    by_base = defaultdict(list)
    for t in TarifaPorcentajeObra.objects.using(db_alias).all():
        by_base[t.tarifa_base_id].append(t)

    for base_id, records in by_base.items():
        if len(records) <= 1:
            continue
        # Keep the one with highest porcentaje_liquidacion
        records.sort(key=lambda t: t.porcentaje_liquidacion, reverse=True)
        keep = records[0]
        delete_ids = [t.id for t in records[1:]]
        TarifaPorcentajeObra.objects.using(db_alias).filter(id__in=delete_ids).delete()
        print(f"  TarifaBase {base_id}: kept id={keep.id}, deleted {len(delete_ids)} duplicates")


def reverse_consolidation(apps, schema_editor):
    """Reverse: no-op since we can't recover deleted records."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("liquidaciones", "0019_remove_inspectorperiodo_inspector_and_more"),
    ]

    operations = [
        # Data consolidation BEFORE field removal
        migrations.RunPython(
            consolidate_tarifa_porcentaje_obra,
            reverse_consolidation,
        ),
        # Remove especialidad from historical table first (historicalmodels tracked before live)
        migrations.RemoveField(
            model_name="historicaltarifaporcentajeobra",
            name="especialidad",
        ),
        # Remove especialidad from live table
        migrations.RemoveField(
            model_name="tarifaporcentajeobra",
            name="especialidad",
        ),
    ]
