# Data migration: seed TipoLiquidacion records and backfill FK

from django.db import migrations


def seed_tipo_liquidacion(apps, schema_editor):
    """Create 6 TipoLiquidacion records if they don't exist."""
    TipoLiquidacion = apps.get_model("liquidaciones", "TipoLiquidacion")

    records = [
        {"codigo": "EDIFICACION", "nombre": "Edificación"},
        {"codigo": "HABILITACION_URBANA", "nombre": "Habilitación Urbana"},
        {"codigo": "MECANICA_SUELOS", "nombre": "Mecánica de Suelos"},
        {"codigo": "IMPACTO_VIAL", "nombre": "Impacto Vial"},
        {"codigo": "TALUDES", "nombre": "Taludes"},
        {"codigo": "INSPECCION_OBRA", "nombre": "Inspección de Obra"},
    ]

    for record in records:
        TipoLiquidacion.objects.get_or_create(
            codigo=record["codigo"],
            defaults={"nombre": record["nombre"]},
        )


def backfill_fk(apps, schema_editor):
    """Backfill tipo_liquidacion_fk from tipo_liquidacion CharField."""
    LiquidacionGeneral = apps.get_model("liquidaciones", "LiquidacionGeneral")
    TipoLiquidacion = apps.get_model("liquidaciones", "TipoLiquidacion")

    # Build lookup: codigo -> TipoLiquidacion instance
    tipo_map = {
        t.codigo: t for t in TipoLiquidacion.objects.all()
    }

    # Backfill each LiquidacionGeneral
    updated = 0
    for liquidacion in LiquidacionGeneral.objects.exclude(tipo_liquidacion__isnull=True):
        codigo = liquidacion.tipo_liquidacion
        if codigo in tipo_map and liquidacion.tipo_liquidacion_fk is None:
            liquidacion.tipo_liquidacion_fk = tipo_map[codigo]
            liquidacion.save(update_fields=["tipo_liquidacion_fk"])
            updated += 1

    # Print for logging
    print(f"[data migration] Backfilled {updated} LiquidacionGeneral records.")


def reverse_migration(apps, schema_editor):
    """No rollback needed for seed; FK backfill is one-way."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("liquidaciones", "0011_add_tipo_liquidacion_fk_to_liquidaciongeneral"),
    ]

    operations = [
        migrations.RunPython(seed_tipo_liquidacion, reverse_migration),
        migrations.RunPython(backfill_fk, reverse_migration),
    ]
